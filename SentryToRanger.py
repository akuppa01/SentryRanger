import argparse
import json
import os
import logging
import requests
from pathlib import Path
from getpass import getpass
from turtle import update
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVICE_NAME = None
RANGER_ADMIN_HOST = None
RANGER_ADMIN_USERNAME = None
RANGER_ADMIN_PASSWORD = None
RANGER_ADMIN_IP = None
INPUT_FILE = None
PORT = "6182"

logging.basicConfig(filename="LogFiles/SentryRanger.log", level=logging.DEBUG,format='%(asctime)s, %(name)s:%(levelname)s: %(message)s',filemode="w")

roles = {}     # dict of {"role name" : role object}
resources = {} # dict of {"resource name" : resource object}
jsonFiles = {} # dict of {"resource name" : json FILE}
errorResources = {} # dict of {"resource name" : resource object} for those policies without any assigned group

class Resource:
    """Resource class stores key information for each policy"""
    def __init__(self): 
        self.resourceStr = None
        self.columnName = "*"
        self.tableName = "*"
        self.databaseName = None
        self.uriName = None
        self.serviceName =  SERVICE_NAME 
        self.isURI = False
        self.description = "description TBD"
        self.labels = {}  # { 'role name' : set('select' , 'All') }


class Role:
    """Role class stores key information for each role"""
    def __init__(self): 
        self.roleName = "DEFAULT"
        self.resources = set()
        self.groups = set()
        self.roleFor = "DEFAULT" # for column/table/database/server

    def set_roleName(self,name):
        self.roleName = name

    def print_role(self): # can be used when debugging
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
                                        "isRecursive": True,
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
    """ 
    Helper function that returns a tuple with policyItems and policyLabels vars
    policyItems, contains permissions info for each role/label
    policyLabels, a list of all the roles
    """
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
    """
    Parses through the Sentry args from input file
    """

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
            currentResource = Resource()
            argPermission = parse_Resource(currentResource, currentRole, arr)
            if argPermission != None:
                createResource(currentResource, currentRole, argPermission)
            else:
                logging.warning("encountered a SERVER related command")

    except Exception as error:
        logging.error(error)
    

def parse_Resource(currentResource, currentRole, arr):
    """
    parses arr (argument) for key information specific to the working resource 
    and updates currentResource and currentRole
    returns specific argPermission and 
    returns None for special cases (like SERVER related commands)
    """
    
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

    # parsing col,tb,db,server
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
            currentRole.roleFor = "server"
            # currentResource.serviceName = arr[4]
            return None
        
        elif arr[3] == "uri": # case[4] -> policy for server
            currentRole.roleFor = "uri"
            currentResource.uriName = arr[4][1:-1]
    
    return argPermission

            
def createResource(currentResource, currentRole, argPermission):
    """
    creates a new resource and update all the key information in currentResource
    also updates the global resources and roles dictionaries with the current resource and role
    """
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
    

def get_arguments():
    """
    Reads input file with Sentry commands and calls parse_arg on each
    """

    args = []
    with open(INPUT_FILE) as f: # reading input file with commands
        args = f.readlines()
    f.close()
    
    for i in range(0,len(args)): # looping through each command
        arg = args[i]    
        parse_arg(arg)


def updateRanger(policy):
    """
    Creates a new policy on Ranger for the policy parameter
    """
    policyName = policy.resourceStr
    print("updating ranger with " + policyName)

    policyJSONname = 'TempFiles/{}.json'.format(policyName)
    headers = {
        'Content-Type': 'application/json',
    }
   
    try:
        url = "https://{}/service/public/v2/api/policy/".format(RANGER_ADMIN_HOST)
        jsonFile = open(policyJSONname)
        jsonData = json.load(jsonFile) 
   
        output = requests.post(url, headers=headers, verify=False, auth=(RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD), json=jsonData )
        if output.status_code == 400: # already existing policy in ranger
            logging.warning("policy with name {} already exits".format(policyName))
            print("policy with name {} already exits".format(policyName))

        elif output.status_code == 200: # policy created succussfully
            logging.info("{} policy successfully created".format(policyName))
            print("{} policy successfully created".format(policyName))


    except Exception as error:
        logging.error("ranger policy creation unsuccessful for " + policy.resourceStr)


def get_serviceName():
    """
    Gets the serivce name for Ranger and updates the global SERVICE_NAME var
    """
    global SERVICE_NAME

    logging.info("in get_service, getting service name...")

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    params = {
        'serviceType': 'hive',
    }
    url =  "https://{}/service/public/v2/api/service/".format(RANGER_ADMIN_HOST)
    try:
        output = requests.get(url, params=params, headers=headers, verify=False, auth=(RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD), timeout=30)
        res = output.json()[0]['name']
        SERVICE_NAME = res
        logging.info("Success! Service name = " +SERVICE_NAME)
        return True
    except Exception as error:
        logging.error("Unable to get service name")
        return False


def validate_file(f):
    """
    checks to see if input parameter f exists, if not then it asks user for new inputFile
    """
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

def deleteRangerPolicies():
    url =  "https://{}/service/public/v2/api/policy".format(RANGER_ADMIN_HOST)

    headers = {
        'Content-Type': 'application/json',
    }

    try:
        files = Path('TempFiles/').glob('*')
        for file in files:
            arr = str(file).split('/')
            policyName = arr[1].replace('.json','')

            params = {
                'servicename': 'kkrkdonotd_hive',
                'policyname': policyName
            }
            output = requests.delete(url, params=params, headers=headers, verify=False, auth=(RANGER_ADMIN_USERNAME, RANGER_ADMIN_PASSWORD))
            
            if output.status_code == 204:
                print(policyName + " successfully deleted from Ranger")


    except Exception as error:
        logging.error("problem when trying to delete Ranger policies")

def argParseCommand(): ## in future, connect this function with sentry side; also check to make sure the provided file path leads to a Sentry/SQL test file
    """
    Parses the command line argument and executes given flags
    -h : general help 
    --input : Provides user to either provide an inputFile or uses default file to read Sentry Commands from
    --delete : deletes all the json files in TempFiles directory and their corresponding Ranger policies as well
    """
    global INPUT_FILE

    parser = argparse.ArgumentParser(description="Read file from Command line.")
    parser.add_argument("-i", "--input", dest="filename", required=False, type=validate_file,
                        help="provide path to input file", metavar="FILE")
    parser.add_argument('--delete', action='store_true',help="deletes all the json files in TempFiles directory and their corresponding Ranger policies as well")
    args = parser.parse_args()

    if (args.delete): #user chose to delete policies
        print("deleting jsons form TempFiles and corresponding policies in Ranger")
        logging.warning("deleting jsons form TempFiles and corresponding policies in Ranger")

        deleteRangerPolicies()
        os.popen("rm -f TempFiles/*.json").read()
        return False

    INPUT_FILE = args.filename
    if args.filename == "default" or INPUT_FILE == None:
        INPUT_FILE = 'InputFiles/sample_input.txt' ## in future, change to sentry side created input file
    print("Reading from INPUT FILE =>", INPUT_FILE,"\n")
    return True

def login():
    """
    asks user to enter ip, username, password information 
    program stops running if user fails to provide correct info after MAX_LOGIN_ATTEMPTS
    updates the global host, username, password, ip vars once user enters correct login details
    returns True if successful login and False otherwise
    """
    global RANGER_ADMIN_HOST
    global RANGER_ADMIN_USERNAME 
    global RANGER_ADMIN_PASSWORD
    global RANGER_ADMIN_IP

    MAX_LOGIN_ATTEMPTS = 3
    host = None
    username = None
    password = None
    loggedIn = False

    os.popen("rm -f TempFiles/*.json").read()
    for i in range(MAX_LOGIN_ATTEMPTS):
        host = input("Enter the public IP of RANGER_ADMIN_HOST: ")
        host_port = host + ":" + PORT
        username = input('Username: ')
        password = getpass(prompt='Password: ', stream=None)
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        params = {
            'serviceType': 'hive',
        }
        url =  "https://{}/service/public/v2/api/service/".format(host_port)
        output = None
        try:
            output = requests.get(url, params=params, headers=headers, verify=False, auth=(username, password), timeout=30)
   
        except: # host is unreachable
            print("Could not connect to host. Please check if host is reachable!\n")

        print("status code",output.status_code)
  
        if output.status_code == 401: # wrong user/pass
            print("Incorrect host or username or password. Please try again!\n")
        if output.status_code == 200: #login successful
            print("\n\nCongrats, login successful!\n")
            loggedIn = True
            break

    if loggedIn:
        RANGER_ADMIN_HOST = host_port
        RANGER_ADMIN_USERNAME = username
        RANGER_ADMIN_PASSWORD = password
        RANGER_ADMIN_IP = host
    else:
        print("\n\nSorry, You ran out of login attempts")

    return loggedIn

        

if __name__ == "__main__":

    run_program = argParseCommand()
    if run_program:
        loggedIn = login() 
        if loggedIn:
            serviceExists = get_serviceName()
            if serviceExists:
                get_arguments()
                for i in resources:
                    cpj = create_policy_json(resources[i])
                    if cpj: #json file successfully created for this resource
                        updateRanger(resources[i])
                        print("")
                        pass
                pass
            pass
    



"""
*** DELETE BEFORE PUSHING CODE ***
Current IP, User, Pass info:

150.136.204.120
admin
OracleTeamUSA!123
"""