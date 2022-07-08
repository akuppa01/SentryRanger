import argparse
import json
from turtle import update

policies = {}

class Policy:

    def __init__(self):
        self.policyName = "DUMMY"

        self.columnName = "DUMMY"
        self.tableName = "DUMMY"
        self.databaseName = "DUMMY"
        self.serviceName = "amoghadint_hive"

        self.groupName = "DUMMY"
        self.policyDescription = "DUMMY"
        self.grantType = "DUMMY" # select/all
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
        
        if arg[-2] != ';': # check if arg is a comment
            # print("check B", arg[-2])
            return
        
        currentPolicy = Policy()
        if arr[0] == "create" and arr[1] == 'role':
            print("check 1")
            currentPolicy = Policy()
            policyName = arr[-1].split(';')[0]
            currentPolicy.set_policyName(policyName)
            policies[policyName] = currentPolicy

        elif arr[0] == "grant" and arr[1] == 'role': #assigning policy to a group
            print("check 2")
            # TODO: add precon to check if role exists beforehand??
            policyName = arr[2]
            group = arr[-1].split(';')[0]
            if policies.get(policyName) != None:
                currentPolicy = policies[policyName]
            else:
                currentPolicy.set_policyName(policyName)
                policies[policyName] = currentPolicy
            currentPolicy.groupName = group
        
        else:
            print("check 3")
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
        print("check end")
    except Exception as error:
        print("error", error)
    

# Get command line arguments and print help
def get_arguments(inputfile):
    # INFO: to read stuff from command line, refer to Prasoon's original code and use argparse module
    args = []
    with open(inputfile) as f: # reading input file with commands
        args = f.readlines()
    f.close()
    

    for i in range(7):#len(args)): # looping through each command
        arg = args[i]
        print('arg {}: {}'.format(i+1,arg))    
        parse_arg(arg)

    # parse_arg(args[0])


# Start
if __name__ == "__main__":
    inputfile = 'InputFiles/GroupAssign.txt'
    get_arguments(inputfile)
    print("policies len", len(policies))
    for i in policies:
        create_policy_json(policies[i])