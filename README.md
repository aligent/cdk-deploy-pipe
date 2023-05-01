# Aligent CDK Deploy Pipe

A BitBucket pipe to deploy CDK Stacks

## Terminologies

### Static Config

Static config is a `yaml` script which can be used to configure and customise the behaviour of the cdk commands.

```yaml
cdk-pipe:
  commands:
    cdk:
      bootstrap: npx cdk bootstrap
      deploy: npx cdk deploy
      synth: npx cdk synth
      diff: npx cdk diff
    npm:
      checks:
        lint: npm run lint
        format: npm run format
      install: npm ci
  beforeScripts:
    - npm version
  afterScripts:
    - echo "Deployment is completed"
```

The default static script can be altered at runtime by setting `CDK_CONFIG_PATH` environment variable.
It is mandatory to set CDK commands using the static scripts.

### Before and After scripts

As the name suggests, the before and after scripts can be used to extend the behaviour.
Both `static config script` and environment variables (`CDK_BEFORE_SCRIPT`, `CDK_AFTER_SCRIPT`) can be used in the context.
When setting before and after scripts using environment variables, use `;` to separate the statements.

### Linting and Formatting Checks  

Linting and Formatting checks against the CDK code can be executed at runtime.  
Required packages and configurations should be included as a apart of the infrastructure code.  
The default execution commands are defined as a part of [static config]  

```yaml
cdk-pipe:
  commands:
    cdk:
      ...
    npm:
      checks:
        lint: npm run lint
        format: npm run format
      ...
```

*Note: If the linting and formatting commands in package.json supposed to auto-correct the issues, you may either use a custom `static config` file with a custom set of commands, or `CHECK_LINT_CMD`/`CHECK_FORMAT_CMD` to override them*  
__If `CHECK_LINT_CMD`/`CHECK_FORMAT_CMD` has been set, it is not required to set `CHECK_LINT`/`CHECK_FORMAT`__

### CDK_EXTRA_ARGS

`CDK_EXTRA_ARGS` environment variable only to be associated, when it is required to append additional arguments to `cdk deploy` command.
For example, `CDK_EXTRA_ARGS='--require-approval never'` will extend the deploy command to `cdk deploy --require-approval never`

If it is required to extend `diff`, `synth` or `bootstrap` commands, `CDK_EXTRA_ARGS_DIFF`, `CDK_EXTRA_ARGS_SYNTH` and `CDK_EXTRA_ARGS_BOOTSTRAP` environment variables should be used.

## YAML Definition

Minimum configuration

```yaml
- step:
    name: "CDK Deploy"
    script:
    - pipe: docker://aligent/cdk-deploy-pipe
    variables: 
        AWS_ACCESS_KEY_ID=AWSACCESSKEYID123
        AWS_SECRET_ACCESS_KEY=awssecretaccesskey@#1232
```

## Variables

| Variable | Usage | Defaults |
|:----------|:-------|:-------|
| AWS_ACCESS_KEY_ID             | AWS access key id for CDK deployment                                                        |   N/A                 |
| AWS_SECRET_ACCESS_KEY         | AWS secret key for CDK deployment                                                           |   N/A                 |
| AWS_DEFAULT_REGION            | Default AWS region                                                                          |   `Nil`               |
| CDK_ROOT_DIR                  | The working directory where the `cdk` commands should executed                              |   `./`                |
| DEBUG                         | To enable debug logs                                                                        |   `false`             |
| CDK_BOOTSTRAP                 | Set this to `true` if it is required to bootstrap the stack prior to the deployment         |   `false`             |
| CDK_SYNTH                     | Set this to `true` if it is required to run synth on the stack prior to the deployment      |   `false`             |
| CDK_DIFF                      | Set this to `true` if it is required to run diff on the stack prior to the deployment       |   `false`             |
| CDK_DEPLOY                    | Set this to `false` to skip CDK deployment                                                  |   `true`              |
| CDK_BEFORE_SCRIPT             | Set to extend the before script which is configured using the static config                 |   `Nil`               |
| CDK_AFTER_SCRIPT              | Set to extend the after script which is configured using the static config                  |   `Nil`               |
| CDK_EXTRA_ARGS                | Set to extend CDK deployment statement which is configured in the static config             |   `Nil`               |
| CDK_CONFIG_PATH               | Set this if a custom static config should be associated                                     |   `./cdk-config.yml`  |
| CHECK_LINT                    | Set this to `true` to validate the linting                                                  |  `false`              |
| CHECK_FORMAT                  | Set this to `true` to validate the formatting                                               |  `false`              |
| CHECK_LINT_CMD                | Use this to override default linting command from [static config], *(this would set `CHECK_LINT`)*                             |  `false`              |
| CHECK_FORMAT_CMD              | Use this to override default formatting command from [static config], *(this would set `CHECK_FORMAT`)*                        |  `false`              |

## Development

To build and run locally

```sh
    # cd into the root directory
    docker build -t cdk-pipe:dev .
    docker run -e AWS_ACCESS_KEY_ID=AWSACCESSKEYID1212 -e AWS_SECRET_ACCESS_KEY=AWSSCRETKEYACCESSKEY1212 -e CDK_ROOT_DIR='./' -e CDK_EXTRA_ARGS='--require-approval never' -e DEBUG=true cdk-pipe:dev
```

To execute the cdk processes, python [subprocess] library has been used. To alter this with a new library use `__scriptRunner()` function

```python
    def __scriptRunner(self, working_dir, arr):
        # Change working Directory
        ...
        while i < len(arr):
            try:
                output = subprocess.run(str(arr[i]).strip().split(" "), check=True)
                combined_output += ["exec => {} returned {}".format(arr[i], output.returncode)]
            ...
        return True, combined_output
```

[subprocess]:(https://docs.python.org/3/library/subprocess.html)  
[static config]:cdk-config.yml
