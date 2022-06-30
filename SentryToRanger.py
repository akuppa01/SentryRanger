import argparse
import json

def create_policy_json():
    jsonFile = open('TemplateFiles/createpolicy.json')
    tmpJsonFile = open('TempFiles/tmpcreatepolicy.json', 'w')
    jsonData = json.load(jsonFile)
    newPolicyName = {"name": policyName,}
    newServiceName = {"service": serviceName, }
    jsonData.update(newPolicyName)
    jsonData.update(newServiceName)
    json.dump(jsonData, tmpJsonFile)
    jsonFile.close()
    tmpJsonFile.close()


# Get command line arguments and print help
def get_arguments():
    global serviceName
    global policyName
    global databaseName
    global tableName
    global columnName
    global groupName


    arg_parser = argparse.ArgumentParser(description='Command line argument for sentry to ranger migration')
    arg_parser.add_argument('-d', '--debug', default='False',
                            help="Set 'True' to enable debug")
    arguments = arg_parser.parse_args()
    debug = arguments.debug

    serviceName = "amoghadint_hive"
    policyName = "prasoonHiveNew1"
    databaseName = "PkDB"
    tableName = "PkTable"
    columnName = "AA"
    groupName = "BigData"

# Start
if __name__ == "__main__":
    get_arguments()
    create_policy_json()