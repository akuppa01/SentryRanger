import argparse
import json
import os
import logging
import subprocess
from getpass import getpass
from turtle import update

SERVICE_NAME = None
RANGER_ADMIN_HOST = None
RANGER_ADMIN_USERNAME = None
RANGER_ADMIN_PASSWORD = None
INPUT_FILE = None

roles = {}     # dict of {"role name" : role object}
resources = {} # dict of {"resource name" : resource object}
jsonFiles = {} # dict of {"resource name" : json FILE}
errorResources = {} # dict of {"resource name" : resource object} for those policies without any assigned group

"""
Any Ranger Policy at minimum needs

policyName, serviceName, database/URI name, 1 permission, 1 group

"""
class Resource:
    """Resource class stores key information for each policy"""
    def __init__(self): 
        self.resourceStr = None
        self.columnName = "*"
        self.tableName = "*"
        self.databaseName = None
        self.uriName = None
        self.serviceName =  SERVICE_NAME ## TODO: change it to parameter
                                         ## TODO: what to do if a command asks for server change
        self.isURI = False
        self.description = "description TBD"
        self.labels = {}  # { 'role name' : set('select' , 'All') }



class Role:
    """Role class stores key information for each role"""
    def __init__(self): ## TODO: account for cases where DUMMY has not been changed/re-assigned
        self.roleName = "DUMMY"
        self.resources = set()
        self.groups = set()
        self.roleFor = "DEFAULT" # for column/table/database/server

    def set_roleName(self,name):
        self.roleName = name

    def print_policy(self):
        print ("Role: " + self.roleName)
        print ("   roleFor: " + self.roleFor)
        print ("   groups: {}".format(self.groups))       
    

def create_policy_json(policy):
    """
    Given a policy parameter, this func creates corresponding json file and adds it to TempFiles directory
    if function returns None, it means json FILE was not created
    if function returns True, json FILE was created successfully
    """
    
    jsonFile = open('TemplateFiles/createpolicy.json')
    jsonData = json.load(jsonFile) 
    
    res = getPolicyItems(policy)
    policyItems = res[0]
    policyLabels = res[1]

    if len(policyLabels) == 0:
        logging.warning("no groups assigned to any of the roles in this resource => " + policy.resourceStr)
        errorResources[policy.resourceStr] = policy
        return None
    
    policy.description = str(policyLabels)
    jsonData.update( {"name": policy.resourceStr, } )
    jsonData.update( {"service": policy.serviceName, } )
    jsonData.update( {"description": policy.description, } )

    if policy.uriName != None: # this policy is for a URL
        jsonData.update( {
                                "resources": {
                                    "url": {
                                        "values": ["{}".format(policy.uriName)],
                                        "isRecursive": False,
                                        "isExcludes": False
                                    }
                                },
                         } )
    else: # this policy is not for a URL
        jsonData.update( {
                                "resources": {
                                    "database": {
                                        "values": [policy.databaseName],
                                        "isRecursive": False,
                                        "isExcludes": False
                                    },
                                    "table": {
                                        "values": [policy.tableName],
                                        "isRecursive": False,
                                        "isExcludes": False
                                    },
                                    "column": {
                                        "values": [policy.columnName],
                                        "isRecursive": False,
                                        "isExcludes": False
                                    }
                                }
                            } )
    
    jsonData.update( { "policyItems": policyItems, } )
    jsonData.update( { "policyLabels": policyLabels, } )

    policyJSONfile = open('TempFiles/{}.json'.format(policy.resourceStr), 'w')
    json.dump(jsonData, policyJSONfile, indent = 2)
    jsonFiles[policy.resourceStr] = policyJSONfile
    jsonFile.close()
    policyJSONfile.close()
    return True

def getPolicyItems(policy):
    policyLabels = []
    policyItems = []
    for role in policy.labels:
        if len(roles[role].groups) != 0:
            policyLabels.append("(Sentry-Migrated)-"+role)
            accesses = []
            for permission in policy.labels[role]:
                accesses.append( {
                                    "isAllowed": True, 
                                    "type": permission
                                 } )
            
            policyItems.append( {
                                    "accesses": accesses, 
                                    "groups": list(roles[role].groups)
                                } )
    
    return (policyItems, policyLabels)
            

def parse_arg(arg):
    # TODO: add preconditions to check for valid commands

    arr = arg.strip().lower().split(" ")

    try:
        if len(arr) == 0 or len(arr) == 1: # check if arg is an empty line 
            return
        
        if arg.rstrip()[-1] != ';': # check if arg is a comment
            return
        
        
        currentRole = Role()
        if arr[0] == "create" and arr[1] == 'role': ## ignore this command maybe??
            logging.warning("encountered a 'create role' command for " + arr[2] )
            return

        if arr[0] == "grant" and arr[1] == 'role': # assigning policy to a group
            currentRole.roleName = arr[2]
            group = arr[-1].split(';')[0]
          
            roleName = currentRole.roleName

            if roles.get(roleName) != None: # role exists
                currentRole = roles[roleName]
            else: # new role
                roles[roleName] = currentRole
            currentRole.groups.add(group)

        else: # normal grant command
            ## TODO: add precon / check for spelling error
            currentResource = Resource()
            argPermission = parse_Resource(currentResource, currentRole, arr)
            if argPermission != None:
                createResource(currentResource, currentRole, argPermission)
            else:
                logging.warning("encountered a SERVER related command")

    except Exception as error:
        logging.error(error)
    

def parse_Resource(currentResource, currentRole, arr):
    
    argRole = arr[-1].split(';')[0] # remove semicolons from name
    currentRole.roleName = argRole

    argPermission = ""

    ## parsing permissions 
    if arr[1] == 'select':
        argPermission = 'select'
    elif arr[1] == 'insert':
        argPermission = 'update'
    else: # handles all other permissions
        argPermission = arr[1].capitalize()

    
    currentResource.labels = {argRole : set([argPermission])} 

    ## parsing col,tb,db,server
    if arr[2][0] == "(" and arr[3] == "on" and arr[4] == "table": # case[1] -> policy for column
        currentRole.roleFor = "column"
        currentResource.columnName = arr[2][1:-1] # remove parentheses
        db_tb = arr[5].split(".")
        currentResource.databaseName = db_tb[0] 
        currentResource.tableName = db_tb[1]

    elif arr[2] == "on":
        if arr[3] == "table": # case[2] -> policy for table
            currentRole.roleFor = "table"
            db_tb = arr[4].split(".")
            currentResource.databaseName = db_tb[0] 
            currentResource.tableName = db_tb[1]
            
        elif arr[3] == "database": # case[3] -> policy for database
            currentRole.roleFor = "database"
            currentResource.databaseName = arr[4]

        elif arr[3] == "server": # case[4] -> policy for server
            ## DOUBT... what to do if we encounter this case????
            currentRole.roleFor = "server"
            # currentResource.serviceName = arr[4]
            return None
        
        elif arr[3] == "uri": # case[4] -> policy for server
            ## DOUBT... what to do if we encounter this case???? how to parameterize instead of hard coding
            currentRole.roleFor = "uri"
            currentResource.uriName = arr[4][1:-1]
    
    return argPermission

            
def createResource(currentResource, currentRole, argPermission):
    #resource name creation
    resourceStr = "{}.{}.{}".format(currentResource.databaseName,currentResource.tableName,currentResource.columnName)
    resourceStr = resourceStr.replace('*','all')

    if currentRole.roleFor == "uri":
        resourceStr = currentResource.uriName.replace("/", "-")[1:]
        currentResource.isURI = True

    currentResource.resourceStr = resourceStr
    roleName = currentRole.roleName

    if resources.get(resourceStr) != None: # existing resource

        origResource = resources[resourceStr]
        if origResource.labels.get(roleName) != None: # role exists in original resource's label
            origResource.labels[roleName].add(argPermission)
        else: # new role
            origResource.labels[roleName] = set([argPermission])
            
        currentResource = origResource

    resources[resourceStr] = currentResource # line needed for both new and existing resources

    if roles.get(roleName) == None: # new role
        roles[roleName] = currentRole
    

# Get command line arguments and print help
def get_arguments():
    # INFO: to read from command line, refer to Prasoon's original code and use argparse module
    args = []
    with open(INPUT_FILE) as f: # reading input file with commands
        args = f.readlines()
    f.close()
    
    for i in range(0,len(args)): # looping through each command
        arg = args[i]    
        parse_arg(arg)


def updateRanger(policy):
    policyName = policy.resourceStr
    policyJSONname = '{}.json'.format(policyName)

    try:
        CREATE_COMMAND = "curl -s -k -u '{}:{}' -X POST -H \"Content-Type: application/json\" -d @TempFiles/\"{}\" https://{}/service/public/v2/api/policy/".format(RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD, policyJSONname, RANGER_ADMIN_HOST)    
        output = os.popen(CREATE_COMMAND).read()

    except Exception as error:
        logging.error("ranger policy creation unsuccessful for " + policy.resourceStr)


def get_serviceName():
    global SERVICE_NAME

    print("in get_service")
    # print("foo",RANGER_ADMIN_HOST, RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD)
    GET_COMMAND = "curl -s -k -u '{}:{}' -H \"Content-Type: application/json\" -H \"Accept: application/json\" -X GET https://{}/service/public/v2/api/service/?serviceType=hive".format(RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD, RANGER_ADMIN_HOST)
    # print(GET_COMMAND)
    output = os.popen(GET_COMMAND).read()
    # print("check before")
    # print(output)
    # print("check after")
    # print()
    # print(output.strip())
    res = json.loads(output)[0]['name']
    SERVICE_NAME = res
    # SERVICE_NAME = "kkrkdonotd_hive"

def validate_file(f):
#     print(type(f))
      curr = f
      while True:
            fileExists = os.path.exists(curr)
            if not fileExists :
                print("{} does not exist".format(curr))
                curr = input('Please enter a different filepath or type "default" to continue with default Input File: ')
                if curr == "default":
                    break
            else:
                break
      return curr

def get_inputFile(): ## in future, connect this function with sentry side; also check to make sure the provided file path leads to a Sentry/SQL test file
    global INPUT_FILE

    parser = argparse.ArgumentParser(description="Read file from Command line.")
    parser.add_argument("-i", "--input", dest="filename", required=False, type=validate_file,
                        help="input file", metavar="FILE")
    args = parser.parse_args()
    # print(args)
    INPUT_FILE = args.filename
    if args.filename == "default" or INPUT_FILE == None:
        INPUT_FILE = 'InputFiles/scaj-INPUT-FILE.txt' ## in future, change to sentry side created input file
    print("Reading from INPUT FILE =>", INPUT_FILE,"\n")

def setup():
    global RANGER_ADMIN_HOST
    global RANGER_ADMIN_USERNAME 
    global RANGER_ADMIN_PASSWORD

    host = None
    username = None
    password = None
    loggedIn = False

    os.popen("rm -f TempFiles/*.json").read()
    for i in range(3):
        host = input("Enter the public IP of RANGER_ADMIN_HOST: ")
        username = input('Username: ')
        password = getpass(prompt='Password: ', stream=None)
        
        # print("check 1")
        GET_COMMAND = "curl -v --connect-timeout 5 -k -u '{}:{}' -H \"Content-Type: application/json\" -H \"Accept: application/json\" -X GET https://{}/service/public/v2/api/service/".format(username, password, host)
        output = os.popen(GET_COMMAND)
        # print("check 2")

        # print(output)
        ## Note: these are a bit hard coded, might need to change later
        if "Connection timed out" in output:
            print("Could not connect to host. Please check if host is reachable!\n")
        elif '{"statusCode":401,"msgDesc":"Authentication Failed"}' in output: # wrong user/pass
            print("Incorrect host or username or password. Please try again!\n")
        elif '"displayName"' in output: #login successful
            print("\n\nCongrats, login successful!\n")
            loggedIn = True
            break
        # print(type(output))
        # print(host, username, password)
        # print(output)
    if loggedIn:
        RANGER_ADMIN_HOST = host
        RANGER_ADMIN_USERNAME = username
        RANGER_ADMIN_PASSWORD = password
    else:
        print("\n\nSorry, You ran out of login attempts")

    return loggedIn

        
"""
129.80.66.56:6182
admin
OracleTeamUSA!123
"""
if __name__ == "__main__":
 
    loggedIn = setup() # login related info
    if loggedIn:
        get_inputFile()

        get_serviceName()
        # print(RANGER_ADMIN_HOST,RANGER_ADMIN_PASSWORD,RANGER_ADMIN_USERNAME, INPUT_FILE, SERVICE_NAME)
        get_arguments()

        print(resources)
        for i in resources:
            cpj = create_policy_json(resources[i])
            if cpj: #json file successfully created for this resource
                updateRanger(resources[i])
                pass
        pass