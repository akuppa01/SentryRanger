import argparse
import json
import os
import logging
from turtle import update


RANGER_ADMIN_HOST = '129.80.66.56:6182'
SERVICE_NAME = "kkrkdonotd_hive"

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
        self.resourceStr = "DUMMY"
        self.columnName = "*"
        self.tableName = "*"
        self.databaseName = "*"
        self.uriName = "not set"
        self.serviceName =  SERVICE_NAME ## TODO: change it to parameter
                                         ## TODO: what to do if a command asks for server change
        self.isURI = False
        self.description = "description TBD"
        self.labels = {}  # { 'role name' : set('select' , 'All') ,}



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
        logging.error("no groups assigned to any of the roles in this resource => " + policy.resourceStr)
        errorResources[policy.resourceStr] = policy
        return None
    
    policy.description = str(policyLabels)
    jsonData.update( {"name": policy.resourceStr, } )
    jsonData.update( {"service": policy.serviceName, } )
    jsonData.update( {"description": policy.description, } )

    if policy.uriName != "not set": # this policy is for a URL
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
            policyLabels.append(role)
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

    # print("\n")
    # print(arr)
    # print("\n")
    try:
        if len(arr) == 0 or len(arr) == 1: # check if arg is an empty line 
            # print("check A")
            return
        
        if arg.rstrip()[-1] != ';': # check if arg is a comment
            # print("check B", arg.rstrip()[-1])
            return
        
        
        currentRole = Role()
        if arr[0] == "create" and arr[1] == 'role': ## ignore this command maybe??
            logging.warning("encountered a 'create role' command for " + arr[2] )
            return

        if arr[0] == "grant" and arr[1] == 'role': # assigning policy to a group
            # print("check 2") 
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
            # print("check 3")
            currentResource = Resource()
            argPermission = parse_Resource(currentResource, currentRole, arr)
            if argPermission != None:
                createResource(currentResource, currentRole, argPermission)
            else:
                logging.warning("encountered a SERVER related command")

        # print("check end")
    except Exception as error:
        logging.error(error)
    

def parse_Resource(currentResource, currentRole, arr):
    
    
    argRole = arr[-1].split(';')[0] # remove semicolons from name
    currentRole.roleName = argRole

    argPermission = ""

    ## parsing permissions 
    if arr[1] == 'select':
        argPermission = 'select'
    else: # handles all other permissions
        argPermission = arr[1].capitalize()

    
    currentResource.labels = {argRole : set([argPermission])} 

    ## parsing col,tb,db,server
    if arr[2][0] == "(" and arr[3] == "on" and arr[4] == "table": # case[1] -> policy for column
        # print("check 1")
        currentRole.roleFor = "column"
        currentResource.columnName = arr[2][1:-1] # remove parentheses
        db_tb = arr[5].split(".")
        currentResource.databaseName = db_tb[0] 
        currentResource.tableName = db_tb[1]

    elif arr[2] == "on":
        # print("check 2")
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
    resourceStr = "{}.{}.{}".format(currentResource.databaseName,currentResource.tableName,currentResource.columnName)
    resourceStr = resourceStr.replace('*','all')
    # print(resourceStr)
    # print(currentRole.roleFor)
    if currentRole.roleFor == "uri":
        resourceStr = currentResource.uriName.replace("/", "-")[1:]
        currentResource.isURI = True
        # print("nai")
    # print("check 4") 
    currentResource.resourceStr = resourceStr
    roleName = currentRole.roleName

    #### by this point, labels have been updated
    if resources.get(resourceStr) != None: # existing resource
        # print("check 4.1")
        origResource = resources[resourceStr]
        # { 'role name' : [ 'select' , 'All' ] }
        if origResource.labels.get(roleName) != None: # role exists in original resource's label
            origResource.labels[roleName].add(argPermission)
        else: # new role
            origResource.labels[roleName] = set([argPermission])
            
        currentResource = origResource

    resources[resourceStr] = currentResource # line needed for both new and existing resources


    # goes to top of method
    
    # print("*** policyName",policyName, policies.get(policyName) != None)

    if roles.get(roleName) == None: # new role
        # print("check 4.2")        
        roles[roleName] = currentRole
    

# Get command line arguments and print help
def get_arguments(INPUT_FILE):
    # INFO: to read stuff from command line, refer to Prasoon's original code and use argparse module
    args = []
    with open(INPUT_FILE) as f: # reading input file with commands
        args = f.readlines()
    f.close()
    
    # aaa
    for i in range(0,len(args)): # looping through each command
        arg = args[i]
        # print("\n")
        # print('arg {}: {}'.format(i+1,arg))    
        parse_arg(arg)

    # parse_arg(args[0])


def updateRanger(policy):
    policyName = policy.resourceStr
    # policyName = "role_1_write_db"
    policyJSONname = '{}.json'.format(policyName)
    # policyJSONname = "role_1_read_policy.json"
    # The command you want to execute   
    # cmd = ['curl', '-ivk', '-u', "'admin:OracleTeamUSA!123'", '-H', '"Content-Type: application/json"', '-X', 'GET', '"https://129.80.66.56:6182/service/public/v2/api/policy?policyName=role_1_read"']
    # temp = subprocess.Popen(cmd)#, stdout = subprocess.PIPE) 
    # GET_COMMAND = "curl -ivk  -u 'admin:OracleTeamUSA!123' -H \"Content-Type: application/json\" -X GET \"https://129.80.66.56:6182/service/public/v2/api/policy?policyName={}\"".format(policyName)
    # print("updateRanger; check 1")
    try:
        # UPDATE_COMMAND = "curl -ivk -u 'admin:OracleTeamUSA!123' -X PUT -H \"Content-Type: application/json\" -d @TempFiles/" + policyJSONname + " https://" + RANGER_ADMIN_HOST + "/service/public/v2/api/service/{\"" + policy.serviceName + "\"}/policy/{\"" + policyName + "\"}/"
        # print(UPDATE_COMMAND)
        # output = os.popen(GET_COMMAND).read()
        # gg = output.split()
        # print("updateRanger; check 2")
        # if (gg[-2]=='Not' and gg[-1]=='found'): #CREATE command
        # if (gg[-1] == "[]"):
        # print("createRanger; check 3", policy.resourceStr)
        CREATE_COMMAND = "curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H \"Content-Type: application/json\" -d @TempFiles/\"{}\" https://{}/service/public/v2/api/policy/".format(policyJSONname, RANGER_ADMIN_HOST)    
        output = os.popen(CREATE_COMMAND).read()
        # print(CREATE_COMMAND)

            # gg = output.split()

        # TODO: add another if statement to check that policy was added successfully
        # print("-------")
        # print(gg)
        # print(gg[-2],gg[-1])
    except Exception as error:
        print("Ranger Policy creation ERROR :", error)


    

# Start
if __name__ == "__main__":
    INPUT_FILE = 'InputFiles/scaj-INPUT-FILE.txt'

    get_arguments(INPUT_FILE)
    # print("roles len", len(roles))
    # print("roles =", roles.keys())
    # for i in roles:
    #     print(i, roles[i].groups)
    # print("")
    # print("resources =")
    # i = "d1.nitish_column.id"
    for i in resources:
        # print(i, resources[i].labels)
        cpj = create_policy_json(resources[i])
        # if cpj:
        #     updateRanger(resources[i])


    # print("\n")
    # print(errorResources.keys())
    # for i in policies:
    
    # print(policies["admin_role"].policyName)
    