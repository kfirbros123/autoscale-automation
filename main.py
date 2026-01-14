import boto3

# --- AWS credentials ---
aws_access_key_id = "access"
aws_secret_access_key = "secret"
aws_session_token = "token"
region_name = "us-east-1"

# --- AWS variables ---
vpc="vpc-0fd581580b59f8d29"
subnet="subnet-07d5e49c3a9d0518c"
image='ami-0d03b8975f8354317'
securityGroup='sg-0dca345f4c0814660'

# --- Clients ---
ec2_client = boto3.client(
    'ec2',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token = aws_session_token,
    region_name=region_name
)
autoscaling_client = boto3.client(
    'autoscaling',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token = aws_session_token,
    region_name=region_name
)
elbv2_client = boto3.client(
    'elbv2',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token = aws_session_token,
    region_name=region_name
)

# --- Step 1: Create Target Group ---
tg_name="cpu-target-group"
tg_response = elbv2_client.create_target_group(
    Name=tg_name,
    Protocol='TCP',
    Port=80,
    VpcId=vpc,  # replace with your VPC ID
    TargetType='instance'
)
target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
print("Target Group ARN:", target_group_arn)

# --- Step 2: Create Network Load Balancer ---
nlb_name="cpu-LB"
nlb_response = elbv2_client.create_load_balancer(
    Name=nlb_name,
    Subnets=[subnet],  # replace with your subnets
    Scheme='internet-facing',
    Type='network',
)
nlb_arn = nlb_response['LoadBalancers'][0]['LoadBalancerArn']
print("NLB ARN:", nlb_arn)

# --- Step 2b: Create Listener for NLB ---
listener_response = elbv2_client.create_listener(
    LoadBalancerArn=nlb_arn,
    Protocol='TCP',
    Port=80,
    DefaultActions=[{
        'Type': 'forward',
        'TargetGroupArn': target_group_arn
    }]
)
listener_arn = listener_response['Listeners'][0]['ListenerArn']
print("Listener ARN:", listener_arn)

# --- Step 3: Create Launch Template ---
lt_name='cpu-burner-template'
launch_template_response = ec2_client.create_launch_template(
    LaunchTemplateName=lt_name,
    LaunchTemplateData={
        'ImageId': image,  # replace with your AMI
        'InstanceType': 't3.medium',
        'KeyName': 'kfir-key',            # replace with your key pair
        'NetworkInterfaces': [
            {
                'DeviceIndex': 0,
                'SubnetId': subnet,  # replace with your subnet
                'AssociatePublicIpAddress': True,
                'Groups': [securityGroup]       # your security group(s)
            }
        ]
        
    }
)
launch_template_id = launch_template_response['LaunchTemplate']['LaunchTemplateId']
print("Launch Template ID:", launch_template_id)

# --- Step 4: Create Auto Scaling Group attached to NLB Target Group ---
asg_name = "cpu-burner-autoscaling"

asg_response = autoscaling_client.create_auto_scaling_group(
    AutoScalingGroupName=asg_name,
    LaunchTemplate={
        'LaunchTemplateId': launch_template_id,
        'Version': '$Latest'
    },
    MinSize=2,
    MaxSize=5,
    DesiredCapacity=2,
    VPCZoneIdentifier=subnet,
    TargetGroupARNs=[target_group_arn],  # attach NLB target group
    Tags=[{
        'Key': 'Name',
        'Value': 'MyASGInstance2',
        'PropagateAtLaunch': True
    }]
)

print("Auto Scaling Group created and attached to NLB:", asg_response)



# --- Step 4: Create Dynamic Scaling Policy ---
pol_name = 'cpu-policy'
policy_response = autoscaling_client.put_scaling_policy(
    AutoScalingGroupName=asg_name,
    PolicyName= pol_name,
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization'
        },
        'TargetValue': 50.0,  # keep average CPU around 50%
        'DisableScaleIn': False
    }
)

policy_arn = policy_response['PolicyARN']
print("Dynamic Scaling Policy ARN:", policy_arn)
