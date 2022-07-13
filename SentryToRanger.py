import argparse
import json
from sre_constants import ASSERT
import subprocess
import os
from turtle import update

HOST_NUMBER = '129.80.66.56:6182'

policies = {}
resources = {}


class Policy:

    def __init__(self): ## TODO: account for cases where DUMMY has not been changed/re-assigned
        self.policyName = "DUMMY"

        self.resources = "DUMMY"
        self.columnName = "DUMMY"
        self.tableName = "DUMMY"
        self.databaseName = "DUMMY"
        self.serviceName = "kkrkdonotd_hive" ## TODO: change it to parameter

        self.groupName = []
        self.policyDescription = []
        self.grantType = []#"select" # select/all
        self.policyFor = "DUMMY" # for column/table/database/server
        self.policyJSONfile = "DUMMY"
        self.jsonFile = "DUMMY"
        self.jsonData = "DUMMY"

    def set_policyName(self,name):
        self.policyName = name
        self.jsonFile = open('TemplateFiles/createpolicy.json')
        self.policyJSONfile = open('TempFiles/{}_policy.json'.format(name), 'w')
        self.jsonData = json.load(self.jsonFile)           
    

def create_policy_json(policy):

    # jsonFile = open('TemplateFiles/createpolicy.json')
    # tmpJsonFile = open('TempFiles/tmpcreatepolicy.json', 'w')

    policy.jsonData.update( {"name": policy.policyName,} )
    policy.jsonData.update( {"service": policy.serviceName, } )
    policy.jsonData.update( {"description": policy.policyDescription, } )

    policy.jsonData.update( {
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
    policy.jsonData.update( {
                                "policyItems": [
                                    {
                                        "accesses": [
                                            {
                                            "isAllowed": True, 
                                            "type": policy.grantType
                                            }, 
                                            {
                                            "isAllowed": True, 
                                            "type": "update"
                                            }, 
                                            {
                                            "isAllowed": True, 
                                            "type": "create"
                                            }
                                        ], 
                                        "groups": [
                                            policy.groupName
                                        ]
                                    }
                                ]
                            } )

    json.dump(policy.jsonData, policy.policyJSONfile, indent = 2)
    policy.jsonFile.close()
    policy.policyJSONfile.close()


def parse_arg(arg):
    # TODO: add preconditions to check for valid commands

    arr = arg.strip().lower().split(" ")
    # print(arr)
    try:
        if len(arr) == 0 or len(arr) == 1: # check if arg is an empty line 
            print("check A")
            return
        
        if arg.rstrip()[-1] != ';': # check if arg is a comment
            print("check B", arg.rstrip()[-1])
            return
        
        currentPolicy = Policy()
        if arr[0] == "create" and arr[1] == 'role':
            # print("check 1")
            currentPolicy = Policy()
            policyName = arr[-1].split(';')[0]
            currentPolicy.set_policyName(policyName)
            policies[policyName] = currentPolicy

        elif arr[0] == "grant" and arr[1] == 'role': #assigning policy to a group
            # print("check 2")
            # TODO: add precon to check if role exists beforehand??
            policyName = arr[2]
            group = arr[-1].split(';')[0]
            if policies.get(policyName) != None:
                currentPolicy = policies[policyName]
            else:
                currentPolicy.set_policyName(policyName)
                policies[policyName] = currentPolicy
            currentPolicy.groupName = group
        
        else: ## TODO: add precon / check for spelling error
            # print("check 3")
            policyName = arr[-1].split(';')[0] # remove semicolons from name

            # create new Policy class object and initialize
            if policies.get(policyName) != None:
                currentPolicy = policies[policyName]
            else:
                currentPolicy.set_policyName(policyName)
                policies[policyName] = currentPolicy

            if arr[1] == 'select':
                currentPolicy.grantType = 'select'
            elif arr[1] == 'all':
                currentPolicy.grantType = 'All'

            
            if arr[2][0] == "(" and arr[3] == "on" and arr[4] == "table": # case[1] -> policy for column
                # print("check 1")
                currentPolicy.policyFor = "column"
                currentPolicy.policyDescription = "create policy for " + currentPolicy.policyFor
                currentPolicy.columnName = arr[2][1:-1] # remove parentheses
                db_tb = arr[5].split(".")
                currentPolicy.databaseName = db_tb[0] 
                currentPolicy.tableName = db_tb[1]

            elif arr[2] == "on":
                # print("check 2")
                if arr[3] == "table": # case[2] -> policy for table
                    currentPolicy.policyFor = "table"
                    db_tb = arr[4].split(".")
                    currentPolicy.databaseName = db_tb[0] 
                    currentPolicy.tableName = db_tb[1]
                    
                if arr[3] == "database": # case[3] -> policy for database
                    currentPolicy.policyFor = "database"
                    currentPolicy.databaseName = arr[4]

                if arr[3] == "server": # case[4] -> policy for server
                    currentPolicy.policyFor = "server"
                    currentPolicy.serviceName = arr[4]

                currentPolicy.policyDescription = "create policy for " + currentPolicy.policyFor
        # print("check end")
    except Exception as error:
        print("error", error)
    

# Get command line arguments and print help
def get_arguments(INPUT_FILE):
    # INFO: to read stuff from command line, refer to Prasoon's original code and use argparse module
    args = []
    with open(INPUT_FILE) as f: # reading input file with commands
        args = f.readlines()
    f.close()
    

    for i in range(23,len(args)):#len(args)): # looping through each command
        arg = args[i]
        print('arg {}: {}'.format(i+1,arg))    
        parse_arg(arg)

    # parse_arg(args[0])


def updateRanger(policy):
    # policyName = policy.policyName
    policyName = "role_1_write_db"
    policyJSONname = '{}_policy.json'.format(policyName)
    # policyJSONname = "role_1_read_policy.json"
    # The command you want to execute   
    # cmd = ['curl', '-ivk', '-u', "'admin:OracleTeamUSA!123'", '-H', '"Content-Type: application/json"', '-X', 'GET', '"https://129.80.66.56:6182/service/public/v2/api/policy?policyName=role_1_read"']
    # temp = subprocess.Popen(cmd)#, stdout = subprocess.PIPE) 
    GET_COMMAND = "curl -ivk  -u 'admin:OracleTeamUSA!123' -H \"Content-Type: application/json\" -X GET \"https://129.80.66.56:6182/service/public/v2/api/policy?policyName={}\"".format(policyName)
    print("updateRanger; check 1")
    try:
        # UPDATE_COMMAND = "curl -ivk -u 'admin:OracleTeamUSA!123' -X PUT -H \"Content-Type: application/json\" -d @TempFiles/" + policyJSONname + " https://" + HOST_NUMBER + "/service/public/v2/api/service/{\"" + policy.serviceName + "\"}/policy/{\"" + policyName + "\"}/"
        # print(UPDATE_COMMAND)
        output = os.popen(GET_COMMAND).read()
        gg = output.split()
        print("updateRanger; check 2")
        # if (gg[-2]=='Not' and gg[-1]=='found'): #CREATE command
        if (gg[-1] == "[]"):
            print("updateRanger; check 3")
            CREATE_COMMAND = "curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H \"Content-Type: application/json\" -d @TempFiles/{} https://{}/service/public/v2/api/policy/".format(policyJSONname, HOST_NUMBER)    
            # output = os.popen(CREATE_COMMAND).read()
            print(CREATE_COMMAND)

            # gg = output.split()

        # TODO: add another if statement to check that policy was added successfully
        print("-------")
        # print(gg)
        # print(gg[-2],gg[-1])
    except Exception as error:
        print("Ranger Policy Update ERROR :", error)


    

# Start
if __name__ == "__main__":
    INPUT_FILE = 'InputFiles/SentryCommands.txt'
    # HOST_NUMBER = '129.80.66.56:6182'
    # inputfile = 'InputFiles/GroupAssign.txt'
    get_arguments(INPUT_FILE)
    print("policies len", len(policies))
    # print(policies)
    for i in policies:
        
    # print(policies["admin_role"].policyName)
        create_policy_json(policies[i])
    # updateRanger(policies["role_1_read"])