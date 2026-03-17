import boto3
import logging
import threading
import time

from botocore.exceptions import ClientError
from checklist import checklistCleanup as cc
from checklist import checklistExecutor as ce
from datetime import datetime, timezone


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
checklist_table = dynamodb.Table('Checklist')

def monitor_checklists():
    while True:
        try:
            # Scan the checklist table for all items
            response = checklist_table.scan()
            current_time = datetime.now(timezone.utc)

            # Iterate over each checklist item
            for checklist in response.get('Items', []):
                checklist_name = checklist['checklist_name']
                start_time = datetime.fromisoformat(checklist.get('start_time'))
                checklist_in_progress = checklist.get('in_progress', False)
                checklist_is_settled = checklist.get('is_settled', False)

                # Logic based on flags and time
                if not checklist_in_progress and not checklist_is_settled:
                    if start_time > current_time:
                        # Checklist is not yet started
                        continue
                    elif start_time <= current_time:
                        # Checklist should start now
                        logger.info(f"Checklist '{checklist_name}' has started. Invoking Checklist Executor.")
                        
                        # Set in_progress flag to prevent duplicate processing
                        checklist_table.update_item(
                            Key={'checklist_name': checklist_name},
                            UpdateExpression='SET in_progress = :val',
                            ExpressionAttributeValues={':val': True}
                        )

                        # Start checklist executor in a separate thread
                        thread = threading.Thread(target=ce.execute_checklist, args=(checklist_name,))
                        thread.daemon = True
                        thread.start()
                        
                        # ce.execute_checklist(checklist_name)
                elif checklist_in_progress and not checklist_is_settled:
                    # Checklist is in progress, do nothing
                    continue
                elif checklist_is_settled:
                    # Checklist has ended, invoke cleanup
                    logger.info(f"Checklist '{checklist_name}' has settled. Starting Cleanup.")
                    cc.cleanup_checklist(checklist_name)

            # Sleep for 5 minutes before the next check
            time.sleep(300)

        except ClientError as e:
            logger.error(f"Error monitoring checklists: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")


def main():
    logger.info("Starting Checklist Monitor Service...")
    monitor_checklists()


if __name__ == "__main__":
    main()