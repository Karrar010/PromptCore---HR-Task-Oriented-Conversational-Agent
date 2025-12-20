"""
Slack service for sending messages via Slack API.
Deterministic action execution - no LLM reasoning.
"""

from typing import Optional, Dict, Any, List
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackService:
    """
    Slack service for sending messages.
    Deterministic - executes actions based on intent and slots.
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        """Initialize Slack service."""
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment variables. Please set it in .env file.")
        self.client = WebClient(token=self.bot_token)
    
    def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel or DM.
        Returns: {'success': bool, 'ts': str, 'error': str}
        """
        try:
            # If channel starts with #, try to find the channel ID first
            if channel.startswith('#'):
                channel_name = channel.lstrip('#')
                channel_id = self.find_channel_by_name(channel_name)
                if channel_id:
                    channel = channel_id
                else:
                    # Try using the channel name directly (Slack API accepts channel names)
                    channel = channel_name
            
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            
            return {
                'success': True,
                'ts': response['ts'],
                'error': None
            }
        
        except SlackApiError as e:
            error_response = e.response
            if error_response and 'channel_not_found' in str(error_response):
                # Try to find the channel and retry
                if not channel.startswith('#'):
                    # Try with #
                    channel_id = self.find_channel_by_name(channel)
                    if channel_id:
                        try:
                            response = self.client.chat_postMessage(
                                channel=channel_id,
                                text=text,
                                thread_ts=thread_ts
                            )
                            return {
                                'success': True,
                                'ts': response['ts'],
                                'error': None
                            }
                        except:
                            pass
            
            return {
                'success': False,
                'ts': None,
                'error': str(e)
            }
    
    def send_dm(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Send a direct message to a user.
        Returns: {'success': bool, 'ts': str, 'error': str}
        """
        try:
            # Open DM channel
            dm_response = self.client.conversations_open(users=[user_id])
            channel_id = dm_response['channel']['id']
            
            # Send message
            return self.send_message(channel_id, text)
        
        except SlackApiError as e:
            return {
                'success': False,
                'ts': None,
                'error': str(e)
            }
    
    def get_general_channel(self) -> Optional[str]:
        """
        Find the general channel in the workspace.
        Returns channel ID or None.
        """
        try:
            channels = self.list_channels()
            # Look for 'general' channel (most workspaces have this)
            for channel in channels:
                name = channel.get('name', '').lower()
                if name == 'general':
                    return channel['id']
            return None
        except Exception as e:
            print(f"Error finding general channel: {e}")
            return None
    
    def get_workspace_admins(self) -> List[str]:
        """
        Get list of workspace admin user IDs.
        Returns list of user IDs.
        """
        try:
            users = []
            cursor = None
            while True:
                response = self.client.users_list(cursor=cursor, limit=200)
                if response['ok']:
                    for user in response['members']:
                        # Check if user is admin or owner
                        if user.get('is_admin') or user.get('is_owner'):
                            users.append(user['id'])
                    cursor = response.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
                else:
                    break
            return users
        except Exception as e:
            print(f"Error getting workspace admins: {e}")
            return []
    
    def execute_request_time_off(
        self,
        message_content: str,
        employee_name: str,
        manager_channel: Optional[str] = None,
        manager_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute request_time_off action.
        Sends notification to manager via Slack.
        Falls back to general channel or workspace admins if HR channel not found.
        """
        # If user ID provided, send DM
        if manager_user_id:
            result = self.send_dm(manager_user_id, message_content)
            if result['success']:
                return result
        
        # If channel provided, try it first
        if manager_channel:
            result = self.send_message(manager_channel, message_content)
            if result['success']:
                return result
            # If failed, continue to fallback
        
        # Try to find HR channel automatically
        hr_channel = self.get_best_channel_for_intent("request_time_off")
        if hr_channel:
            result = self.send_message(hr_channel, message_content)
            if result['success']:
                return result
        
        # Try common HR channel names
        for channel_name in ["all-hr-agent-com", "all-hr", "hr-agent-com", "hr-agent", "hr"]:
            channel_id = self.find_channel_by_name(channel_name)
            if channel_id:
                result = self.send_message(channel_id, message_content)
                if result['success']:
                    return result
        
        # Fallback 1: Try general channel
        general_channel = self.get_general_channel()
        if general_channel:
            print(f"HR channel not found, sending to general channel instead")
            result = self.send_message(general_channel, message_content)
            if result['success']:
                return {
                    'success': True,
                    'ts': result.get('ts'),
                    'error': None,
                    'note': 'Message sent to general channel (HR channel not found)'
                }
        
        # Fallback 2: Try sending to workspace admins
        admins = self.get_workspace_admins()
        if admins:
            print(f"Channels not found, sending to workspace admins instead")
            success_count = 0
            for admin_id in admins[:3]:  # Limit to first 3 admins
                result = self.send_dm(admin_id, message_content)
                if result['success']:
                    success_count += 1
            
            if success_count > 0:
                return {
                    'success': True,
                    'ts': None,
                    'error': None,
                    'note': f'Message sent to {success_count} workspace admin(s) (channels not found)'
                }
        
        return {
            'success': False,
            'error': 'No HR channel, general channel, or workspace admins found. Please create a channel like #all-hr-agent-com or set MANAGER_CHANNEL in environment.'
        }
    
    def execute_schedule_meeting(
        self,
        message_content: str,
        participants: List[str],
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute schedule_meeting action.
        Sends meeting details to participants.
        """
        results = []
        
        if channel:
            # Send to channel
            result = self.send_message(channel, message_content)
            results.append(result)
        else:
            # Send DMs to participants
            for participant_id in participants:
                result = self.send_dm(participant_id, message_content)
                results.append(result)
        
        # Check if all succeeded
        all_success = all(r['success'] for r in results)
        
        return {
            'success': all_success,
            'results': results,
            'error': None if all_success else 'Some messages failed to send'
        }
    
    def execute_submit_it_ticket(
        self,
        message_content: str,
        it_channel: Optional[str] = None,
        it_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute submit_it_ticket action.
        Posts ticket to IT support channel or sends DM to IT user.
        """
        # If channel ID provided, use it directly
        if it_channel:
            return self.send_message(it_channel, message_content)
        
        # If user ID provided, send DM
        if it_user_id:
            return self.send_dm(it_user_id, message_content)
        
        # Try to find IT channel automatically
        try:
            it_channels = self.find_it_channels()
            if it_channels:
                # Prefer channels with 'it-support' or 'support' in name
                for channel in it_channels:
                    name = channel.get('name', '').lower()
                    if 'it-support' in name or 'support' in name:
                        return self.send_message(channel['id'], message_content)
                # Otherwise use first IT channel
                return self.send_message(it_channels[0]['id'], message_content)
        except Exception as e:
            print(f"Error finding IT channel: {e}")
        
        # Fallback: try common channel names
        for channel_name in ["#it-support", "#it-help", "#tech-support", "#support"]:
            channel_id = self.find_channel_by_name(channel_name.lstrip('#'))
            if channel_id:
                return self.send_message(channel_id, message_content)
        
        return {
            'success': False,
            'error': 'No IT channel found. Please create an IT support channel or set IT_CHANNEL in environment.'
        }
    
    def execute_file_medical_claim(
        self,
        message_content: str,
        hr_channel: Optional[str] = None,
        hr_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute file_medical_claim action.
        Sends claim to HR department.
        Falls back to general channel or admins if HR channel not found.
        """
        # If user ID provided, send DM
        if hr_user_id:
            result = self.send_dm(hr_user_id, message_content)
            if result['success']:
                return result
        
        # If channel provided, try it first
        if hr_channel:
            result = self.send_message(hr_channel, message_content)
            if result['success']:
                return result
        
        # Try to find HR channel automatically
        hr_channel_id = self.get_best_channel_for_intent("file_medical_claim")
        if hr_channel_id:
            result = self.send_message(hr_channel_id, message_content)
            if result['success']:
                return result
        
        # Try common HR channel names
        for channel_name in ["all-hr-agent-com", "all-hr", "hr-agent-com", "hr-agent", "hr"]:
            channel_id = self.find_channel_by_name(channel_name)
            if channel_id:
                result = self.send_message(channel_id, message_content)
                if result['success']:
                    return result
        
        # Fallback: Try general channel
        general_channel = self.get_general_channel()
        if general_channel:
            print(f"HR channel not found, sending to general channel instead")
            result = self.send_message(general_channel, message_content)
            if result['success']:
                return {
                    'success': True,
                    'ts': result.get('ts'),
                    'error': None,
                    'note': 'Message sent to general channel (HR channel not found)'
                }
        
        # Last resort: Try workspace admins
        admins = self.get_workspace_admins()
        if admins:
            print(f"Channels not found, sending to workspace admins instead")
            success_count = 0
            for admin_id in admins[:3]:
                result = self.send_dm(admin_id, message_content)
                if result['success']:
                    success_count += 1
            
            if success_count > 0:
                return {
                    'success': True,
                    'ts': None,
                    'error': None,
                    'note': f'Message sent to {success_count} workspace admin(s) (channels not found)'
                }
        
        return {
            'success': False,
            'error': 'No HR channel, general channel, or workspace admins found. Please create a channel like #all-hr-agent-com or set HR_CHANNEL in environment.'
        }
    
    def get_user_by_email(self, email: str) -> Optional[str]:
        """
        Get Slack user ID by email.
        Returns user ID or None if not found.
        """
        try:
            response = self.client.users_lookupByEmail(email=email)
            if response['ok']:
                return response['user']['id']
            return None
        except SlackApiError:
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID.
        """
        try:
            response = self.client.users_info(user=user_id)
            if response['ok']:
                return response['user']
            return None
        except SlackApiError:
            return None
    
    def list_channels(self, types: str = "public_channel") -> List[Dict[str, Any]]:
        """
        List all channels in the workspace.
        Only lists public channels (we don't have groups:read scope for private channels).
        Returns list of channel dictionaries.
        """
        try:
            channels = []
            cursor = None
            
            while True:
                response = self.client.conversations_list(
                    types=types,  # Only public channels
                    cursor=cursor,
                    limit=200
                )
                
                if response['ok']:
                    channels.extend(response['channels'])
                    cursor = response.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
                else:
                    # If error, try with just public channels
                    if 'missing_scope' in str(response.get('error', '')):
                        print(f"Note: Only listing public channels (missing groups:read scope)")
                        break
                    break
            
            return channels
        except SlackApiError as e:
            error_str = str(e)
            if 'missing_scope' in error_str or 'groups:read' in error_str:
                print(f"Note: Only listing public channels (missing groups:read scope for private channels)")
                return []
            print(f"Error listing channels: {e}")
            return []
    
    def find_channel_by_name(self, channel_name: str) -> Optional[str]:
        """
        Find channel ID by name (with or without #).
        Returns channel ID or None if not found.
        """
        channel_name = channel_name.lstrip('#').lower()
        channels = self.list_channels()
        
        for channel in channels:
            if channel.get('name', '').lower() == channel_name:
                return channel['id']
        
        return None
    
    def find_hr_channels(self) -> List[Dict[str, Any]]:
        """
        Find HR-related channels in the workspace.
        Looks for channels with 'hr', 'human-resources', 'all-hr' in the name.
        """
        channels = self.list_channels()
        hr_channels = []
        
        hr_keywords = ['hr', 'human-resources', 'human_resources', 'all-hr', 'hr-agent', 'hr-agent-com']
        
        for channel in channels:
            channel_name = channel.get('name', '').lower()
            if any(keyword in channel_name for keyword in hr_keywords):
                hr_channels.append(channel)
        
        return hr_channels
    
    def find_it_channels(self) -> List[Dict[str, Any]]:
        """
        Find IT-related channels in the workspace.
        Looks for channels with 'it', 'tech', 'support', 'helpdesk' in the name.
        """
        channels = self.list_channels()
        it_channels = []
        
        it_keywords = ['it', 'tech', 'support', 'helpdesk', 'technical', 'it-support']
        
        for channel in channels:
            channel_name = channel.get('name', '').lower()
            if any(keyword in channel_name for keyword in it_keywords):
                it_channels.append(channel)
        
        return it_channels
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """
        Get workspace information including channels and members.
        """
        try:
            # Get workspace info
            team_info = self.client.team_info()
            
            # Get channels
            channels = self.list_channels()
            hr_channels = self.find_hr_channels()
            it_channels = self.find_it_channels()
            
            # Get users
            users = []
            cursor = None
            while True:
                response = self.client.users_list(cursor=cursor, limit=200)
                if response['ok']:
                    users.extend(response['members'])
                    cursor = response.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
                else:
                    break
            
            return {
                'workspace_name': team_info.get('team', {}).get('name', 'Unknown'),
                'workspace_id': team_info.get('team', {}).get('id', ''),
                'total_channels': len(channels),
                'total_users': len(users),
                'hr_channels': [{'id': c['id'], 'name': c['name']} for c in hr_channels],
                'it_channels': [{'id': c['id'], 'name': c['name']} for c in it_channels],
                'all_channels': [{'id': c['id'], 'name': c['name']} for c in channels[:50]]  # Limit to first 50
            }
        except SlackApiError as e:
            print(f"Error getting workspace info: {e}")
            return {}
    
    def get_best_channel_for_intent(self, intent_name: str) -> Optional[str]:
        """
        Intelligently find the best channel for a given intent.
        Returns channel ID or channel name (without #) that can be used.
        """
        try:
            if intent_name == "request_time_off":
                # Look for HR channels
                hr_channels = self.find_hr_channels()
                if hr_channels:
                    # Prefer channels with 'all-hr' or 'hr-agent' in name
                    for channel in hr_channels:
                        name = channel.get('name', '').lower()
                        if 'all-hr' in name or 'hr-agent' in name or 'hr-agent-com' in name:
                            return channel['id']
                    # Otherwise return first HR channel
                    return hr_channels[0]['id']
                
                # Fallback: try to find by common names
                for name in ['all-hr-agent-com', 'all-hr', 'hr-agent-com', 'hr-agent', 'hr']:
                    channel_id = self.find_channel_by_name(name)
                    if channel_id:
                        return channel_id
            
            elif intent_name == "submit_it_ticket":
                # Look for IT channels
                it_channels = self.find_it_channels()
                if it_channels:
                    # Prefer channels with 'it-support' or 'support' in name
                    for channel in it_channels:
                        name = channel.get('name', '').lower()
                        if 'it-support' in name or 'support' in name:
                            return channel['id']
                    # Otherwise return first IT channel
                    return it_channels[0]['id']
                
                # Fallback: try common IT channel names
                for name in ['it-support', 'it-help', 'tech-support', 'support']:
                    channel_id = self.find_channel_by_name(name)
                    if channel_id:
                        return channel_id
            
            elif intent_name == "file_medical_claim":
                # Look for HR channels
                hr_channels = self.find_hr_channels()
                if hr_channels:
                    return hr_channels[0]['id']
                
                # Fallback
                for name in ['all-hr-agent-com', 'all-hr', 'hr-agent-com', 'hr']:
                    channel_id = self.find_channel_by_name(name)
                    if channel_id:
                        return channel_id
            
            elif intent_name == "schedule_meeting":
                # Look for general or meeting channels
                channels = self.list_channels()
                for channel in channels:
                    name = channel.get('name', '').lower()
                    if 'meeting' in name or 'general' in name:
                        return channel['id']
            
            return None
        except Exception as e:
            print(f"Error finding best channel: {e}")
            return None

