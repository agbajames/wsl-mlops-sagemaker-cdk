from aws_cdk import Stack, Duration, aws_cloudwatch as cw, aws_lambda as _lambda
from constructs import Construct

class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        deploy_lambda: _lambda.Function,
        predict_lambda: _lambda.Function,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        for fn, name in [(deploy_lambda, "DeployEndpoint"), (predict_lambda, "PredictWeekly")]:
            cw.Alarm(
                self,
                f"{name}ErrorsAlarm",
                metric=fn.metric_errors(period=Duration.minutes(5)),
                threshold=0,
                evaluation_periods=1,
                datapoints_to_alarm=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
                alarm_description=f"Lambda {name} has errors.",
            )
