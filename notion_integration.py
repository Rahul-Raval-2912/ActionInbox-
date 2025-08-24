"""Simple Notion integration for ActionInbox"""

import os
import requests
import json
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NotionTaskCreator:
    def __init__(self):
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def is_configured(self) -> bool:
        """Check if Notion is properly configured"""
        return bool(self.api_key and self.database_id)
    
    def create_task(self, title: str, details: str = "", due_date: Optional[str] = None) -> bool:
        """Create a task in Notion database"""
        if not self.is_configured():
            print("Notion not configured - skipping task creation")
            return False
        
        try:
            # Prepare task properties
            properties = {
                "Title": {
                    "title": [{"text": {"content": title[:100]}}]  # Limit title length
                },
                "Status": {
                    "select": {"name": "To Do"}
                },
                "Source": {
                    "select": {"name": "Email"}
                }
            }
            
            # Add due date if provided
            if due_date:
                properties["Due Date"] = {
                    "date": {"start": due_date}
                }
            
            # Add details if provided
            if details:
                properties["Details"] = {
                    "rich_text": [{"text": {"content": details[:2000]}}]  # Limit details length
                }
            
            # Create the page/task
            data = {
                "parent": {"database_id": self.database_id},
                "properties": properties
            }
            
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"Created Notion task: {title}")
                return True
            else:
                print(f"Notion API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Notion integration error: {e}")
            return False

# Global instance
notion_creator = NotionTaskCreator()

def create_notion_task(analysis: dict) -> bool:
    """Create Notion task from email analysis"""
    if not notion_creator.is_configured():
        return False
    
    # Only create tasks for Task classification
    if analysis.get('classification') != 'Task':
        return False
    
    entities = analysis.get('entities', {})
    
    title = entities.get('task_title') or analysis.get('summary', 'Email Task')
    details = entities.get('task_details', '')
    due_date = entities.get('due_date')
    
    return notion_creator.create_task(title, details, due_date)

if __name__ == "__main__":
    # Test the integration
    if notion_creator.is_configured():
        success = notion_creator.create_task(
            "Test Task from ActionInbox",
            "This is a test task created by ActionInbox integration",
            "2024-12-01"
        )
        print(f"Test result: {'Success' if success else 'Failed'}")
    else:
        print("Notion not configured. Set NOTION_API_KEY and NOTION_DATABASE_ID in .env file")