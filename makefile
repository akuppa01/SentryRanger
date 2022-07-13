

default:
	python SentryToRanger.py

# post: (create a policy)
# 	for file in TempFiles:
# 		curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @ll.json https://129.80.21.216:6182/service/public/v2/api/policy
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @role3_policy.json https://129.80.21.216:6182/service/public/v2/api/policy
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @role1_policy.json https://129.80.21.216:6182/service/public/v2/api/policy/
# # service/public/v2/api/service/{service-name}/policy/{policy-name}
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @role1_policy.json https://129.80.21.216:6182/service/public/v2/api/service/{service-name}/policy/{policy-name}

# update by policy name #### curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @role1_policy.json https://129.80.21.216:6182/service/public/v2/api/service/{"amoghadint_hive"}/policy/{"role1"}/
# update with id #### curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @role1_policy.json https://129.80.21.216:6182/service/public/v2/api/policy/73

#GET commands
# ?policyName=emp_policy
# curl -ivk  -u 'admin:OracleTeamUSA!123' -H "Content-Type: application/json" -X GET "https://129.80.21.216:6182/service/public/v2/api/policy/"
# curl -ivk  -u 'admin:OracleTeamUSA!123' -H "Content-Type: application/json" -X GET "https://129.80.21.216:6182/service/public/v2/api/policy?policyName=role1"

# new cluster code
# https://129.80.66.56:6182/service/public/v2/api/policy
# https://129.80.66.56:6182/admin/OracleTeamUSA!123
# curl -ivk  -u 'admin:OracleTeamUSA!123' -H "Content-Type: application/json" -X GET "https://129.80.66.56:6182/service/public/v2/api/policy/"
# curl -ivk  -u 'admin:OracleTeamUSA!123' -H "Content-Type: application/json" -X GET "https://129.80.66.56:6182/service/public/v2/api/policy?policyName=role1"
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @role_1_read_policy.json https://129.80.66.56:6182/service/public/v2/api/policy/

# curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @role_1_read_policy.json https://129.80.66.56:6182/service/public/v2/api/service/{"kkrkdonotd_hive"}/policy/{"role_1_read"}/
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @TempFiles/role_1_read_policy.json https://129.80.66.56:6182/service/public/v2/api/service/{"kkrkdonotd_hive"}/policy/{"role_1_read"}/

# curl -ivk  -u 'admin:OracleTeamUSA!123' -X PUT -H "Content-Type: application/json" -d @TempFiles/role_1_read_policy.json https://129.80.66.56:6182/service/public/v2/api/service/{"kkrkdonotd_hive"}/policy/{"yoo"}/

# curl -ivk  -u 'admin:OracleTeamUSA!123' -H "Content-Type: application/json" -X GET "https://129.80.66.56:6182/service/public/v2/api/policy?policyName=role_1_read"
clean:
	rm -f TempFiles/*.json
