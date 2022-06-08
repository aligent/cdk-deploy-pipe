from distutils.log import error
from email.policy import default
from ensurepip import bootstrap
import io, os , subprocess, yaml
import string, argparse
from bitbucket_pipes_toolkit import Pipe, yaml, get_variable

# Parsser is used to set config file path
# The default path of the config file is './cdk-config.yml'
parser = argparse.ArgumentParser(description='CDK-PIPE Universal BitBucket pipe to execute CDK Stacks.')

# Argument to set config file path
parser.add_argument('--config', 
                    const='cdk-config.yml', default='cdk-config.yml',
                    nargs='?',
                    help='CDK-PIPE config file path')
args = parser.parse_args()

# Variables should be passed as Deployment or Repository variable. 
variables = {
    'AWS_ACCESS_KEY_ID': {'type': 'string', 'required': True},
    'AWS_SECRET_ACCESS_KEY': {'type': 'string', 'required': True},
    'AWS_DEFAULT_REGION': {'type': 'string', 'required': False},
    'CDK_ROOT_DIR': {'type': 'string', 'required': False, 'nullable': True, 'default': './'},
    'DEBUG': {'type': 'boolean', 'required': False, 'default': False},
    'CDK_BOOTSTRAP': {'type': 'boolean', 'required': False, 'default': False},
    'CDK_SYNTH': {'type': 'boolean', 'required': False, 'default': False},
    'CDK_DIFF' : {'type': 'boolean', 'required': False, 'default': False},
    'CDK_DEPLOY' : {'type': 'boolean', 'required': False, 'default': True},
    'CDK_BEFORE_SCRIPT': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_AFTER_SCRIPT': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_EXTRA_ARGS': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_EXTRA_ARGS_DIFF': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_EXTRA_ARGS_SYNTH': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_EXTRA_ARGS_BOOTSTRAP': {'type': 'string', 'required': False, 'nullable': True},
    'CDK_CONFIG_PATH': {'type': 'string', 'required': False, 'nullable': True},
}

class CDKDeployPipe(Pipe):
    config_path = args.config
    working_dir = './'
    static_config = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) 

        # Read Environment Variables
        self.cdk_config_path            = self.get_variable('CDK_CONFIG_PATH')
        self.working_dir                = self.get_variable('CDK_ROOT_DIR')
        self.cdk_bootstrap              = self.get_variable("CDK_BOOTSTRAP")
        self.cdk_deploy                 = self.get_variable("CDK_DEPLOY")
        self.cdk_extra_args             = self.get_variable("CDK_EXTRA_ARGS")
        self.cdk_extra_args_diff        = self.get_variable("CDK_EXTRA_ARGS_DIFF")
        self.cdk_extra_args_synth       = self.get_variable("CDK_EXTRA_ARGS_SYNTH")
        self.cdk_extra_args_bootstrap   = self.get_variable("CDK_EXTRA_ARGS_BOOTSTRAP")
        self.cdk_diff                   = self.get_variable("CDK_DIFF")
        self.cdk_synth                  = self.get_variable("CDK_SYNTH")
        self.cdk_before_script          = self.get_variable('CDK_BEFORE_SCRIPT')
        self.cdk_after_script           = self.get_variable('CDK_AFTER_SCRIPT')

        
        # If custom config file has been provided using environment variable, it should take the precedence
        if self.cdk_config_path is not None:
            self.log_warning('static config script has been altered: ' + self.cdk_config_path) 
            self.config_path = self.cdk_config_path
        try: 
            with io.open(self.config_path, 'r') as stream:
                self.static_config = yaml.load(stream, Loader=yaml.FullLoader)
        except Exception as error:
            self.fail('could not read static config file')

        # Read from static script and validation
        try:
            self.cdk_static_before_script       = self.static_config['cdk-pipe']['beforeScripts']
        except:
            self.log_warning("before script in static config not found")
            self.cdk_static_before_script       = None
        try: 
            self.cdk_static_after_script        = self.static_config['cdk-pipe']['afterScripts']
        except:
            self.log_warning("after script in static config not found")
            self.cdk_static_after_script        = None
        try:
            self.cmd_cdk_synth                  =  self.static_config['cdk-pipe']['commands']['cdk']['synth']
            self.cmd_cdk_diff                   =  self.static_config['cdk-pipe']['commands']['cdk']['diff']
            self.cmd_cdk_deploy                 =  self.static_config['cdk-pipe']['commands']['cdk']['deploy']
            self.cmd_cdk_bootstrap              =  self.static_config['cdk-pipe']['commands']['cdk']['bootstrap']
            self.cmd_npm_install                =  self.static_config['cdk-pipe']['commands']['npm']['install']
        except Exception as error:
            self.fail("could not find the definition for {} in static config".format(error))


            
    # Shell script Runner is an helper function to execute shell scripts
    # Accept an array of shell commands
    # In an event where a statement failed, the function should stop the execution and return false
    def __scriptRunner(self, working_dir, arr):
        # Change the working Directory
        cwd = os.getcwd()
        os.chdir(working_dir)
        i = 0 
        combined_output = []
        while i < len(arr):
            try:
                output = subprocess.run(str(arr[i]).strip().split(" "), check=True)
                combined_output += ["exec => {} returned {}".format(arr[i], output.returncode)]
                i += 1
            except Exception as error:
                return False, error
            finally:
                # Change back to the previous directory
                os.chdir(cwd)
        return True, combined_output

    # Run pre/post scripts
    # If the CDK_BEFORE_SCRIPT/CDK_AFTER_SCRIPT environment variable has been set
    # It will be executed after the execution of scripts in static config file
    def __scripts(self, static_script, runtime_script):
        combined_output = []
        working_dir = self.working_dir

        if static_script is not None:
            status, err = self.__scriptRunner(working_dir, static_script)
            if not status:
                return None, err
            combined_output += err

        if runtime_script is not None and len(runtime_script) > 0:
            status, err = self.__scriptRunner(working_dir, runtime_script.split(";"))
            if not status:
                return None, err
            combined_output += err
        return combined_output, None

    # CDK Function
    # CDK function only return an exception/error when a command failed
    def __cdk(self):
        working_dir = self.working_dir

        # NPM Install
        self.log_info("installing npm packages[{}] => {}".format(self.working_dir,self.cmd_npm_install))
        status, err = self.__scriptRunner(working_dir, [self.cmd_npm_install])
        if not status:
            return Exception('npm install: ' + str(err))     

        # CDK Bootstrap
        if self.cdk_bootstrap:
            try:
                bootstrap_cmd = self.cmd_cdk_bootstrap
                # If bootstrap script should be extended
                if self.cdk_extra_args_bootstrap:
                    extension = self.cdk_extra_args_bootstrap
                    self.log_warning("'{}' has been extended with '{}'".format(bootstrap_cmd, extension))
                    bootstrap_cmd = " ".join((bootstrap_cmd, extension))
                self.log_info("cdk boostrap initiated[{}] => {}".format(self.working_dir,bootstrap_cmd))
                status, err = self.__scriptRunner(working_dir, [bootstrap_cmd])
            except Exception as exception:
                return Exception('cdk bootstrap: ' + str(exception))
            
        # CDK Deploy
        if self.cdk_deploy:
            try:
                deploy_cmd = self.cmd_cdk_deploy
                # If deployment script should be extended
                if self.cdk_extra_args:
                    extension = self.cdk_extra_args
                    self.log_warning("'{}' has been extended with '{}'".format(deploy_cmd, extension))
                    deploy_cmd = " ".join((deploy_cmd, extension))
                self.log_info("cdk deploy initiated[{}] => {}".format(self.working_dir,deploy_cmd))
                status, err = self.__scriptRunner(working_dir, [deploy_cmd])
                if not status:
                    return Exception('cdk deploy: ' + str(err))
            except Exception as exception:
                return Exception('cdk deploy: ' + str(exception))

        # CDK Diff
        if self.cdk_diff:
            try:
                diff_cmd = self.cmd_cdk_diff
                # If diff script should be extended
                if self.cdk_extra_args_diff:
                    extension = self.cdk_extra_args_diff
                    self.log_warning("'{}' has been extended with '{}'".format(diff_cmd, extension))
                    diff_cmd = " ".join((diff_cmd, extension))
                self.log_info("cdk diff initiated[{}] => {}".format(self.working_dir,diff_cmd))
                status, err = self.__scriptRunner(working_dir, [diff_cmd])
                if not status:
                    return Exception('cdk diff: ' + str(err))
            except Exception as exception:
                return Exception('cdk diff: ' + str(exception))

        # CDK Synth
        if self.cdk_synth:
            try:
                synth_cmd = self.cmd_cdk_synth
                # If synth script should be extended
                if self.cdk_extra_args_synth:
                    extension = self.cdk_extra_args_synth
                    self.log_warning("'{}' has been extended with '{}'".format(synth_cmd, extension))
                    synth_cmd = " ".join((synth_cmd, extension))
                self.log_info("cdk synth initiated[{}] => {}".format(self.working_dir,synth_cmd))
                status, err = self.__scriptRunner(working_dir, [synth_cmd])
                if not status:
                    return Exception('cdk synth: ' + str(err))
            except Exception as exception:
                return Exception('cdk synth: ' + str(exception))
           
        return None
    
    def run(self):
        # Print workring dir
        self.log_info('working directory: ' + self.working_dir )

        # execute before script
        combined_output, err =  self.__scripts(self.cdk_static_before_script, self.cdk_before_script)
        if err is not None:
            self.fail(err)
        if len(combined_output) > 0:
            [self.log_info("before script: {}".format(output)) for output in combined_output]


        # cdk deployment
        err = self.__cdk()
        if err is not None:
            self.fail('could not deploy cdk stack: ' + str(err))

        # execute after script
        combined_output, err = self.__scripts(self.cdk_static_after_script, self.cdk_after_script)
        if err is not None:
            self.fail(err)
        if len(combined_output) > 0:
            [self.log_info("after script: {}".format(output)) for output in combined_output]



if __name__ == '__main__':
    with open('/pipe.yml', 'r') as metadata_file:
        metadata = yaml.safe_load(metadata_file.read())
    pipe = CDKDeployPipe(schema=variables, pipe_metadata=metadata, check_for_newer_version=True)
    pipe.run()