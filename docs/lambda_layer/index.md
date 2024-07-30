!!! tip inline end "SageWorks Lambda Layers"
    AWS Lambda Jobs are a great way to spin up data processing jobs. Follow this guide and empower AWS Lambda with SageWorks!

SageWorks makes creating, testing, and debugging of AWS Lambda Functions easy. The exact same [SageWorks API Classes](../api_classes/overview.md) are used in your AWS Lambda Functions. Also since SageWorks manages the access policies you'll be able to test new Lambda Jobs locally and minimizes surprises when deploying.
    
!!! warning inline end "Work In Progress"
    The SageWorks Lambda Layers are a great way to use SageWorks but they are still in 'beta' mode so please let us know if you have any issues.
    
## Lambda Job Setup

Setting up a AWS Lambda Job that uses SageWorks is straight forward. SageWorks can be 'installed' using a Lambda Layer and then you can use the Sageworks API just like normal.

Here are the ARNs for the current SageWorks Lambda Layers, please note they are specified with region and Python version in the name, so if your lambda is us-east-1, python 3.12, pick this ARN with those values in it.
 
**us-east-1**

- arn:aws:lambda:us-east-1:507740646243:layer:sageworks\_lambda_layer-us-east-1-python310:1
- arn:aws:lambda:us-east-1:507740646243:layer:sageworks\_lambda_layer-us-east-1-python311:2
- arn:aws:lambda:us-east-1:507740646243:layer:sageworks\_lambda_layer-us-east-1-python312:1

**us-west-2**

- arn:aws:lambda:us-west-2:507740646243:layer:sageworks\_lambda_layer-us-west-2-python310:1
- arn:aws:lambda:us-west-2:507740646243:layer:sageworks\_lambda_layer-us-west-2-python311:2
- arn:aws:lambda:us-west-2:507740646243:layer:sageworks\_lambda_layer-us-west-2-python312:1

**Note:** If you're using lambdas on a different region or with a different Python version, just let us know and we'll publish some additional layers.

<img alt="lambda_layer"  padding: 20px; border: 1px solid grey;""
src="https://github.com/user-attachments/assets/7d0e2fbe-b907-42bc-96bd-3b274d94c3de">

At the bottom of the Lambda page there's an 'Add Layer' button. You can click that button and specify the layer using the ARN above. Also in the 'General Configuration' set these parameters:

- Timeout: 5 Minutes
- Memory: 4096

**Set the SAGEWORKS_BUCKET ENV**
SageWorks will need to know what bucket to work out of, so go into the Configuration...Environment Variables... and add one for the SageWorks bucket that your are using for AWS Account (dev, prod, etc).
<img alt="lambda_layer"  padding: 20px; border: 1px solid grey;""
src="https://github.com/user-attachments/assets/a5afdaff-188f-45ca-bd66-1ab62d7b0b2a">


!!! tip "Lambda Role Details"
    If your Lambda Function already use an existing IAM Role then you can add the SageWorks policies to that Role to enable the Lambda Job to perform SageWorks API Tasks. See [SageWorks Access Controls](https://docs.google.com/presentation/d/1_KwbaBsyBoiWW_8SEallHg8RMsi9FdK10dr2wwzo3CA/edit?usp=sharing)

## SageWorks Lambda Example
Here's a simple example of using SageWorks in your Lambda Function. 

!!! warning "SageWorks Layer is Compressed"
    The SageWorks Lambda Layer is compressed (*to fit all the awesome*). This means that the `load_lambda_layer()` method must be called before using any other SageWorks imports, see the example below. If you do not do this you'll probably get a `No module named 'numpy'` error or something like that.

```py title="examples/lambda_hello_world.py"
import json
from pprint import pprint
from sageworks.utils.lambda_utils import load_lambda_layer
    
# Load/Decompress the SageWorks Lambda Layer
load_lambda_layer()

# After 'load_lambda_layer()' we can use other SageWorks imports
from sageworks.api import Meta, Model 

def lambda_handler(event, context):
    
    # Create our Meta Class and get a list of our Models
    meta = Meta()
    models = meta.models()
    
    print(f"Number of Models: {len(models)}")
    print(models)
        
    # Onboard a model
    model = Model("abalone-regression")
    pprint(model.details())
        
    # Return success
    return {
        'statusCode': 200,
        'body': { "incoming_event": event}
    }
```

## Lambda Function Local Testing
Lambda Power without the Pain. SageWorks manages the AWS Execution Role/Policies, so local API and Lambda Functions will have the same permissions/access. Also using the same Code as your notebooks or scripts makes creating and testing Lambda Functions a breeze.

```shell
python my_lambda_function.py --sageworks-bucket <your bucket>
```

## Additional Resources
- SageWorks Access Management: [SageWorks Access Management](https://docs.google.com/presentation/d/1_KwbaBsyBoiWW_8SEallHg8RMsi9FdK10dr2wwzo3CA/edit?usp=sharing)
- Setting up SageWorks on your AWS Account: [AWS Setup](../aws_setup/core_stack.md)

<img align="right" src="../images/scp.png" width="180">

- Using SageWorks for ML Pipelines: [SageWorks API Classes](../api_classes/overview.md)

- Consulting Available: [SuperCowPowers LLC](https://www.supercowpowers.com)
