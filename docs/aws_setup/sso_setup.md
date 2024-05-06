# AWS SSO Setup
!!!tip inline end "Need AWS Help?"
    The SuperCowPowers team is happy to give any assistance needed when setting up AWS and SageWorks. So please contact us at [sageworks@supercowpowers.com](mailto:sageworks@supercowpowers.com) or on chat us up on [Discord](https://discord.gg/WHAJuz8sw8) 

## Get some information
  - Goto your AWS Identity Center in the AWS Console
  - On the right side there will be two important pieces of information
    - Start URL
    - Region 

  If you're connecting to the SCP AWS Account you can use these values

  ```
  Start URL: https://supercowpowers.awsapps.com/start 
  Region: us-west-2
  ```


## Install AWS CLI
**Mac** `brew install awscli`
    
**Linux** `pip install awscli`

**Windows**

Download the MSI installer (top right corner on this page) <https://aws.amazon.com/cli/> and follow the installation instructions.

## Running the SSO Configuration 
**Note:** You only need to do this once!

```
aws configure sso --profile <whatever you want> (e.g. aws_sso)
SSO session name (Recommended): sso-session
SSO start URL []: <the Start URL from info above>
SSO region []: <the Region from info above>
SSO registration scopes [sso:account:access]: <just hit return>
```

You will get a browser open/redirect at this point and get a list of available accounts.. something like below, just pick the correct account

```
There are 2 AWS accounts available to you.
> SCP_Sandbox, briford+sandbox@supercowpowers.com (XXXX40646YYY)
  SCP_Main, briford@supercowpowers.com (XXX576391YYY)
```

Now pick the role that you're going to use

```
There are 2 roles available to you.
> DataScientist
  AdministratorAccess

CLI default client Region [None]: <same region as above>
CLI default output format [None]: json
```

## Setting up some aliases for bash/zsh
Edit your favorite ~/.bashrc ~/.zshrc and add these nice aliases/helper

```
# AWS Aliases
alias bob_sso='export AWS_PROFILE=bob_sso'

# Default AWS Profile
export AWS_PROFILE=bob_sso
```

## Testing your new AWS Profile
Make sure your profile is active/set

```
env | grep AWS
AWS_PROFILE=<bob_sso or whatever>
```
Now you can list the S3 buckets in the AWS Account

```
aws ls s3
```
If you get some message like this...

```
The SSO session associated with this profile has
expired or is otherwise invalid. To refresh this SSO
session run aws sso login with the corresponding
profile.
```

This is fine/good, a browser will open up and you can refresh your SSO Token.

After that you should get a listing of the S3 buckets without needed to refresh your token.

```
aws s3 ls
❯ aws s3 ls
2023-03-20 20:06:53 aws-athena-query-results-XXXYYY-us-west-2
2023-03-30 13:22:28 sagemaker-studio-XXXYYY-dbgyvq8ruka
2023-03-24 22:05:55 sagemaker-us-west-2-XXXYYY
2023-04-30 13:43:29 scp-sageworks-artifacts
```

 
## AWS Resources
- [AWS Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html)
- [Users and Groups](https://docs.aws.amazon.com/singlesignon/latest/userguide/users-groups-provisioning.html)
- [Permission Sets](https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html)
- [SSO Command Line/Python Configure](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html)


