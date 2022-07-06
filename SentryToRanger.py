import argparse
import json
from turtle import update

def create_policy_json():

    jsonFile = open('TemplateFiles/createpolicy.json')
    tmpJsonFile = open('TempFiles/tmpcreatepolicy.json', 'w')
    jsonData = json.load(jsonFile)
    newPolicyName = {"name": policyName,}
    newServiceName = {"service": serviceName, }
    newPolicyDescription = {"description": policyDescription, }

    newResource = {
                        "resources": {
                            "database": {
                                "values": [databaseName],
                                "isRecursive": False,
                                "isExcludes": False
                            },
                            "table": {
                                "values": [tableName],
                                "isRecursive": False,
                                "isExcludes": False
                            },
                            "column": {
                                "values": [columnName],
                                "isRecursive": False,
                                "isExcludes": False
                            }
                        }
                    }
    newPolicyItems = {
                        "policyItems": [
                            {
                                "accesses": [
                                    {
                                    "isAllowed": True, 
                                    "type": grantType
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
                                    groupName
                                ]
                            }
                        ]
                    }
    jsonData.update(newPolicyDescription)
    jsonData.update(newResource)
    jsonData.update(newPolicyItems)
    jsonData.update(newPolicyName)
    jsonData.update(newServiceName)
    json.dump(jsonData, tmpJsonFile, indent = 2)
    jsonFile.close()
    tmpJsonFile.close()


def parse_arg(arg):
    # TODO: add preconditions to check for valid commands

    global serviceName
    global policyName
    global databaseName
    global tableName
    global columnName
    global groupName
    global policyDescription
    global grantType
    global policyFor

    serviceName = "DUMMY"
    policyName = "DUMMY"
    databaseName = "DUMMY"
    tableName = "DUMMY"
    columnName = "DUMMY"
    groupName = "DUMMY"
    policyDescription = "DUMMY"
    grantType = "DUMMY" # select/all
    policyFor = "DUMMY" # for column/table/database/server

    arr = arg.strip().lower().split(" ")
    # print(arr)
    try:
        if len(arr) == 0:
            return
        if arr[1] == 'select':
            grantType = 'select'
        elif arr[1] == 'all':
            grantType = 'All'

        
        if arr[2][0] == "(" and arr[3] == "on" and arr[4] == "table": # case[1] -> policy for column
            # print("check 1")
            policyFor = "column"
            policyDescription = "create policy for " + policyFor
            columnName = arr[2][1:-1] # remove parentheses
            db_tb = arr[5].split(".")
            databaseName = db_tb[0] 
            tableName = db_tb[1]

        elif arr[2] == "on":
            # print("check 2")
            if arr[3] == "table": # case[2] -> policy for table
                policyFor = "table"
                db_tb = arr[4].split(".")
                databaseName = db_tb[0] 
                tableName = db_tb[1]
                
            if arr[3] == "database": # case[3] -> policy for database
                policyFor = "database"
                databaseName = arr[4]

            if arr[3] == "server": # case[4] -> policy for server
                policyFor = "server"
                serviceName = arr[4]

            policyDescription = "create policy for " + policyFor

        policyName = arr[-1].split(';')[0] # remove semicolons from name
        groupName = "BigData" # TODO: maybe change later

    except Exception as error:
        print("error", error)
    

# Get command line arguments and print help
def get_arguments():
    # INFO: to read stuff from command line, refer to Prasoon's original code and use argparse module
    args = []
    with open('SentryCommands.txt') as f: # reading input file with commands
        args = f.readlines()
    

    # count = 0
    # for arg in args: # looping through each command
    #     count += 1
    #     print('arg {}: {}'.format(count,arg))    
    #     parse_arg(arg)

    parse_arg(args[0])


# Start
if __name__ == "__main__":
    get_arguments()
    create_policy_json()