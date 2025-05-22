# BabaMuskBot

This project contains source code and supporting files for a serverless Telegram bot that you can deploy with the SAM CLI. It includes the following files and folders:

- `baba_musk_bot/` - Code for the application's Lambda function, including `app.py` (the main handler) and `requirements.txt` (dependencies).
- `events/` - Invocation events that you can use to invoke the function locally (e.g., `event.json`).
- `tests/` - Unit and integration tests for the application code.
- `template.yaml` - An AWS SAM template that defines the application's AWS resources (Lambda function, API Gateway, IAM roles).
- `README.md` - This file, providing guidance on setup, deployment, and usage.

The application uses several AWS resources, including a Lambda function and an API Gateway API. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

If you prefer to use an integrated development environment (IDE) to build and test your application, you can use the AWS Toolkit.  
The AWS Toolkit is an open source plug-in for popular IDEs that uses the SAM CLI to build and deploy serverless applications on AWS. The AWS Toolkit also adds a simplified step-through debugging experience for Lambda function code. See the following links to get started.

* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [Visual Studio](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/welcome.html)

## Deploy the sample application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command (`sam build --use-container`) will build the source of your application using a Docker container, ensuring that the build environment matches the Lambda execution environment. It installs dependencies specified in `baba_musk_bot/requirements.txt` and creates a deployment package.

The second command (`sam deploy --guided`) will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region. A good starting point would be `BabaMuskBot` or a variation.
* **AWS Region**: The AWS region you want to deploy your app to (e.g., `us-east-1`).
* **Parameter TOKEN**: Enter your Telegram Bot Token. This is stored securely in AWS Systems Manager Parameter Store and referenced by the Lambda function.
* **Parameter POLYGONKEY**: Enter your Polygon.io API Key. This is also stored securely and referenced by the Lambda function.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes. (Default: `y`)
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command. (Default: `y`)
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file (`samconfig.toml`) inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application. (Default: `y`)

You can find your API Gateway Endpoint URL (which is the webhook URL for your Telegram bot) in the output values displayed after deployment. This URL needs to be set as your Telegram bot's webhook.

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command. This command compiles your application and installs dependencies specified in `baba_musk_bot/requirements.txt`.

```bash
YourProjectName$ sam build --use-container
```

The SAM CLI creates a deployment package and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives (e.g., a Telegram message). Test events can be found in the `events` folder. For this bot, `events/event.json` can be used as a sample.

Run your Lambda function locally and invoke it with the `sam local invoke` command. Replace `BabaMuskBot` with your stack name if different.

```bash
YourProjectName$ sam local invoke BabaMuskFunction --event events/event.json --env-vars env.json
```
Note: For local invocation to work correctly with environment variables like `TELEGRAM_TOKEN` and `POLYGON_API_KEY`, you'll need to provide them. You can use a local environment variable file (e.g., `env.json`) and pass it with the `--env-vars` flag.
Example `env.json`:
```json
{
  "BabaMuskFunction": {
    "TELEGRAM_TOKEN": "YOUR_TELEGRAM_TOKEN",
    "POLYGON_API_KEY": "YOUR_POLYGON_API_KEY"
  }
}
```

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally (typically on port 3000).

```bash
YourProjectName$ sam local start-api --env-vars env.json
# In another terminal, you can then send a POST request to http://localhost:3000/webhook
# Example using curl with a sample event:
# curl -X POST -H "Content-Type: application/json" -d "@events/event.json" http://localhost:3000/webhook
```

The SAM CLI reads the `template.yaml` to determine the API's routes and the functions they invoke. The `Events` property on the `BabaMuskFunction` definition includes the route (`/webhook`) and method (`post`).

```yaml
Resources:
  BabaMuskFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: baba_musk_bot/
      Handler: app.webhook
      # ... other properties
      Events:
        BabaMusk: # This is the event name, not the function name for invocation
          Type: Api
          Properties:
            Path: /webhook
            Method: post
```

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line.

`NOTE`: This command works for all AWS Lambda functions, not just the ones you deploy using SAM. Replace `BabaMuskBot` with your actual stack name if different.

```bash
YourProjectName$ sam logs -n BabaMuskFunction --stack-name BabaMuskBot --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Tests

Tests are defined in the `tests` folder in this project. The `tests/requirements.txt` file lists dependencies for testing.

```bash
# Navigate to your project directory if not already there
# cd YourProjectName

# Install test dependencies
pip install -r tests/requirements.txt --user

# Run unit tests
python -m pytest tests/unit -v

# Run integration tests (requires the stack to be deployed)
# Set the AWS_SAM_STACK_NAME environment variable to your deployed stack name
AWS_SAM_STACK_NAME=<your-stack-name> python -m pytest tests/integration -v
```

## Bot Commands

Here are the commands you can use with BabaMuskBot:

*   `/hello` or `/start`: Greets the user and introduces the bot.
*   `/ytd <TICKER_SYMBOL>`: Calculates Year-To-Date performance for the given stock ticker. Example: `/ytd AAPL`
*   `/coin`: Fetches current prices for major cryptocurrencies (BTC, ETH, ADA, MATIC, SOL) in USD and CAD.
*   `/desc <TICKER_SYMBOL>`: Provides a business summary for the given stock ticker. Example: `/desc TSLA`
*   `/guide`: Displays this help message with all available commands.

## Configuration

The bot requires the following environment variables to be configured for the Lambda function:

*   `TELEGRAM_TOKEN`: Your Telegram Bot Token. This is used to authenticate with the Telegram API.
*   `POLYGON_API_KEY`: Your Polygon.io API key. This is used to fetch stock market data.

These variables are prompted for during the `sam deploy --guided` process and are stored as parameters in AWS Systems Manager Parameter Store for security. They are then passed to the Lambda function's environment. If you need to update them after deployment, you can do so by re-running `sam deploy --guided` or by updating the parameters directly in the AWS Systems Manager console and then updating the Lambda function's configuration to reference the new versions (if applicable).

## Cleanup

To delete the application that you created, use the AWS CLI. Assuming you used `BabaMuskBot` for the stack name (or replace with your actual stack name), you can run the following:

```bash
aws cloudformation delete-stack --stack-name BabaMuskBot
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond "hello world" samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
