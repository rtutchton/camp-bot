# camp-bot


exploring how to create a text bot for campers 


curl -X POST http://localhost:8080/send-alert -d "message=This is a test alert"


curl -X POST http://localhost:8080/send-alert -H "Content-Type: application/x-www-form-urlencoded"" -d { "message" : "🚨 Camp update: The hike is delayed due to weather!" }


curl -X POST http://localhost:8080/send-alert \
     -H "Content-Type: application/json" \
     -d '{"message":"🚨 Camp update: The hike is delayed due to weather!"}'