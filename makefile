

default:
	python SentryToRanger.py

# post:
# 	for file in TempFiles:
# 		curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @ll.json https://129.80.21.216:6182/service/public/v2/api/policy
# curl -ivk  -u 'admin:OracleTeamUSA!123' -X POST -H "Content-Type: application/json" -d @role1_policy.json https://129.80.21.216:6182/service/public/v2/api/policy

clean:
	rm -f TempFiles/*.json
