# Testing Full ML Pipeline

Now that the core Sageworks AWS Stack has been deployed. Let's test out SageWorks by building a full entire AWS ML Pipeline from start to finish. The script `build_ml_pipeline.py` uses the SageWorks API to quickly and easily build an AWS Modeling Pipeline.

!!! tip inline end "Taste the Awesome"
    The SageWorks "hello world" builds a full AWS ML Pipeline. From S3 to deployed model and endpoint. If you have any troubles at all feel free to contact us at [sageworks email](mailto:sageworks@supercowpowers.com) or on [Discord](https://discord.gg/WHAJuz8sw8) and we're happy to help you for FREE.
    
- DataLoader(abalone.csv) --> DataSource
- DataToFeatureSet Transform --> FeatureSet
- FeatureSetToModel Transform --> Model
- ModelToEndpoint Transform --> Endpoint

This script will take a LONG TiME to run, most of the time is waiting on AWS to finalize FeatureGroups, train Models or deploy Endpoints.

```
❯ python build_ml_pipeline.py
<lot of building ML pipeline outputs>
```
After the script completes you will see that it's built out an AWS ML Pipeline and testing artifacts.

## Run the SageWorks Dashboard (Local)
!!! tip inline end "Dashboard AWS Stack"
    Deploying the Dashboard Stack is straight-forward and provides a robust AWS Web Server with Load Balancer, Elastic Container Service, VPC Networks, etc. (see [AWS Dashboard Stack](dashboard_stack.md))

For testing it's nice to run the Dashboard locally, but for longterm use the SageWorks Dashboard should be deployed as an AWS Stack. The deployed Stack allows everyone in the company to use, view, and interact with the AWS Machine Learning Artifacts created with SageWorks.

```
cd sageworks/application/aws_dashboard
./dashboard
```
**This will open a browser to http://localhost:8000**

<figure">
<img alt="sageworks_new_light" src="https://github.com/SuperCowPowers/sageworks/assets/4806709/5f8b32a2-ed72-45f2-bd96-91b7bbbccff4">
<figcaption>SageWorks Dashboard: AWS Pipelines in a Whole New Light!</figcaption>
</figure>


!!! success
    Congratulations: SageWorks is now deployed to your AWS Account. Deploying the AWS Stack only needs to be done once. Now that this is complete your developers can simply `pip install sageworks` and start using the API.
    
If you ran into any issues with this procedure please contact us via [Discord](https://discord.gg/WHAJuz8sw8) or email [sageworks@supercowpowers.com](mailto:sageworks@supercowpowers.com) and the SCP team will provide **free** setup and support for new SageWorks users.
