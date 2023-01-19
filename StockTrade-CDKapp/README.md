# Stock Trade (Deployed to AWS version)

The Flask app code - the core logic of the app - can be found under serverless_flask/app.py

app.py utilizes helper functions I wrote into serverless_flask/helpers.py

The routes in app.py are imported as a blueprint in serverless_flask/lambda.py and converted to accept the json event input of AWS Lambda's lambda handler using a library called apigw-wsgi.

The infrastructure-as-code setup for the infra of the project (setting up API Gateway Lambda REST API and CloudFront CDN) can be found under lib in the form of a CDK stack which is equivalent to defining a CloudFormation stack (except in this case its through code)
