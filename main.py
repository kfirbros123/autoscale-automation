import boto3

# --- AWS credentials ---
aws_access_key_id = "access"
aws_secret_access_key = "secret"
aws_session_token = "TOKEN"
region_name = "us-east-1"

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
tg_response = elbv2_client.create_target_group(
    Name='new-cpu-burner-tg',
    Protocol='TCP',
    Port=80,
    VpcId='vpc-088019931a2d8797c',  # replace with your VPC ID
    TargetType='instance'
)
target_group_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
print("Target Group ARN:", target_group_arn)

# --- Step 2: Create Network Load Balancer ---
nlb_response = elbv2_client.create_load_balancer(
    Name='my-nlb',
    Subnets=['subnet-02a7120cd95210421'],  # replace with your subnets
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
launch_template_response = ec2_client.create_launch_template(
    LaunchTemplateName='cpu-burner-new-template',
    LaunchTemplateData={
        'ImageId': 'ami-049b59c8203345952',  # replace with your AMI
        'InstanceType': 't3.medium',
        'KeyName': 'kfir-key',            # replace with your key pair
        'NetworkInterfaces': [
            {
                'DeviceIndex': 0,
                'SubnetId': 'subnet-04b96cd3bf4703ab6',  # replace with your subnet
                'AssociatePublicIpAddress': True,
                'Groups': ['sg-06f03bef8203f3391']       # your security group(s)
            }
        ]
        
    }
)
launch_template_id = launch_template_response['LaunchTemplate']['LaunchTemplateId']
print("Launch Template ID:", launch_template_id)

# --- Step 4: Create Auto Scaling Group attached to NLB Target Group ---
asg_name = "cpu-burner-new-asg"

asg_response = autoscaling_client.create_auto_scaling_group(
    AutoScalingGroupName=asg_name,
    LaunchTemplate={
        'LaunchTemplateId': launch_template_id,
        'Version': '$Latest'
    },
    MinSize=1,
    MaxSize=5,
    DesiredCapacity=2,
    VPCZoneIdentifier='subnet-04b96cd3bf4703ab6',
    TargetGroupARNs=[target_group_arn],  # attach NLB target group
    Tags=[{
        'Key': 'Name',
        'Value': 'MyASGInstance',
        'PropagateAtLaunch': True
    }]
)

print("Auto Scaling Group created and attached to NLB:", asg_response)



# --- Step 4: Create Dynamic Scaling Policy ---
policy_response = autoscaling_client.put_scaling_policy(
    AutoScalingGroupName=asg_name,
    PolicyName='CPUScaleOutPolicy',
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization'
        },
        'TargetValue': 50.0,  # keep average CPU around 50%
        'DisableScaleIn': False,
        'EstimatedInstanceWarmup': 120  # 300 seconds = 5 minutes
    }
)

policy_arn = policy_response['PolicyARN']
print("Dynamic Scaling Policy ARN:", policy_arn)
