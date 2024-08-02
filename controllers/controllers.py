from fastapi import Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from models.model import WorkflowChat, WorkflowChatMessage
from supertokens_python.recipe.session import SessionContainer
import openai
import json
from dotenv import load_dotenv
import os

load_dotenv()
openai.api_key =  os.getenv("OPENAI_KEY")

def get_workflow_collection(request: Request):
    return request.app.database["workflows"]

def get_workflow_chat_collection(request: Request):
    return request.app.database["workflowchats"]

def generate_initial_prompt():
    return ("Hello! I'm excited to help you launch your Dripify campaign. To get started, could you tell me what type of campaign you want to create? For example, Welcome Series, Product Launch, Customer Re-engagement, etc.")

def generate_follow_up_question(context):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
                   You are a dripify campaign launch assistant for Dripify(a linkedin automation tool).
  Your tasks are to:

        1. **Collect User Requirements:** Start by asking clear and friendly questions to gather details about the campaign launch. Ensure that each question is specific to one parameter at a time.
        2. **Clarify and Confirm:** If any answers are ambiguous or incomplete, ask follow-up questions to clarify their needs and make sure you have all the necessary information.
        3. **Map Responses:** Use the reference mapping provided below to convert user responses into the appropriate Dripify categories. Validate their inputs and populate the JSON object accordingly.
        4. **Handle Invalid Responses:** When encountering invalid answers, offer examples from the allowed values list. Re-ask the question in a helpful manner until you receive a valid response.
        5. **Allow Modifications:** Users should be able to modify any previously provided parameters. If they request changes, update the existing data as needed.
        6. **Track and Complete:** Keep track of all information gathered. If any details are missing, ask for those specific pieces to complete the campaign setup according to Dripify’s criteria.
        7. **Skipping Questions:** Users can skip questions by leaving them blank or explicitly indicating they want to skip. In such cases, map the skipped parameter to a placeholder value or handle it accordingly.
        8. **Determine Completion:** Monitor user responses for cues indicating they want to finish. If they use phrases like "that's enough" or "I'm done," set 'finished' to true and end the process.
   

  Reference mapping for allowed values:
    - CampaignType: Welcome Series, Product Launch, Customer Re-engagement, Abandoned Cart, Seasonal Promotion, Loyalty Program, Newsletter, Event Invitation
    - AudienceSegment: New Subscribers, Active Customers, Inactive Customers, High-value Customers, First-time Buyers, Repeat Customers, Abandoned Cart Users
    - EmailFrequency: Daily, Every Other Day, Twice a Week, Weekly, Bi-weekly, Monthly
    - CampaignDuration: 3 days, 1 week, 2 weeks, 1 month, 3 months, 6 months, Ongoing
    - ContentType: Promotional, Educational, Testimonials, Product Updates, Company News, User-generated Content, Behind-the-scenes
    - CallToAction: Shop Now, Learn More, Book a Demo, Subscribe, Claim Offer, Join Waitlist, RSVP
    - PersonalizationLevel: Basic (Name), Intermediate (Browsing History), Advanced (Purchase History + Preferences)
    - A/BTestingElements: Subject Lines, Email Content, Send Times, CTAs, Images, Personalization Level
    - SuccessMetrics: Open Rate, Click-through Rate, Conversion Rate, Revenue Generated, List Growth Rate, Unsubscribe Rate

 Example Mapping:
    - For **CampaignType**: If the user responds with "welcome emails for new customers", map to "Welcome Series".
    - For **AudienceSegment**: If the user says "people who have bought before", map to "Repeat Customers".
    - For **EmailFrequency**: If the user mentions "every other day", map to "Every Other Day".
    - For **CampaignDuration**: If the user specifies "about a month", map to "1 month".
    - For **ContentType**: If the user indicates "educational content", map to "Educational".
    - For **CallToAction**: If the user says "get more info", map to "Learn More".
    - For **PersonalizationLevel**: If the user mentions "using their browsing history", map to "Intermediate (Browsing History)".
    - For **A/BTestingElements**: If the user refers to "testing different email subjects", map to "Subject Lines".
    - For **SuccessMetrics**: If the user says "how many people open the emails", map to "Open Rate".
    - For **EndGoal**: If the user mentions "increase sales of our new product", map to "Boost sales of new product launch".
    - For **ListName**: If the user says "new product interested customers", map to "New Product Interest List".
    - For **SavedSearch**: If the user provides "LinkedIn search for tech professionals in California", map to the appropriate LinkedIn search URL or identifier.

  When a response is invalid, provide the user with specific examples from the mapping list and ask them to provide a valid response. Confirm all parameters with the user and request any additional details as needed. Maintain a smooth conversation flow and ensure the user can update their inputs if necessary. End the process when the user indicates they are finished.
                    """
                },
                {
                    "role": "system",
                    "content": """
                    The user may provide responses that need to be mapped to allowed values. Your response should:
                    1. Validate user input against the allowed values specified in the reference mapping.
                    2. Provide examples of valid responses if the input is invalid, using the reference mapping as a guide.
                    3. Confirm the parameters with the user and request any additional details if needed to ensure accurate Campaign Launch criteria.
                    4. Handle requests to change parameters by updating the existing data based on user feedback.
                    5. Maintain the conversation flow by asking the next relevant question from the list of required parameters.
                    6. Determine if the user wants to finish the process based on their responses. If the user indicates they are done (e.g., "that's enough", "finish", "no more details"), set 'finished' to true and conclude the interaction.
                    """
                },
                *context
            ],
            functions=[
                {
                    "name": "update_campaign_info",
                    "description": "Update or add campaign launch parameters based on user input.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "parameter": {"type": "string", "description": "The parameter to update or add"},
                            "value": {"type": "string", "description": "The mapped value for the parameter"},
                            "valid": {"type": "boolean", "description": "Whether the input is valid"},
                            "message": {"type": "string", "description": "Message to display to the user"},
                            "next_question": {"type": "string", "description": "Next question to ask the user"},
                            "finished": {"type": "boolean", "description": "Whether the user wants to finish the process"}
                        },
                        "required": ["parameter", "value", "valid", "message", "next_question", "finished"]
                    }
                }
            ],
            function_call={"name": "update_campaign_info"}
        )
        if hasattr(response.choices[0].message, 'function_call'):
            result = json.loads(response.choices[0].message['function_call']['arguments'])
            return result
        else:
            raise HTTPException(status_code=400, detail="No function call found in the response")
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")
    
def save_workflow_chat_to_json(chat_id: str, data: dict):
    filename = f"campaign_launch_requirements_{chat_id}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def trigger_workflow_chat(request: Request, workflowId: str):
    initial_question = generate_initial_prompt()
    workflow_chat = WorkflowChat(
        workflowid=workflowId,
        messages=[WorkflowChatMessage(question=initial_question)],
        collected_info={}
    )
    workflow_chat_data = jsonable_encoder(workflow_chat)
    new_workflow_chat = get_workflow_chat_collection(request).insert_one(workflow_chat_data)
    if new_workflow_chat.inserted_id:
        return {
            "workFlowChatId": str(new_workflow_chat.inserted_id),
            "question": initial_question,
        }
    else:
        raise HTTPException(status_code=401, detail="Error while creating workflow chat")
    
def continue_workflow_chat(request: Request, chatId: str, user_response: str):
    workflow_chat = get_workflow_chat_collection(request).find_one({"_id": chatId})
    if not workflow_chat:
        raise HTTPException(status_code=404, detail="Workflow chat not found")
    workFlowId = workflow_chat["workflowid"]
    history_messages = workflow_chat["messages"]
    collected_info = workflow_chat.get("collected_info", {})
    last_message = history_messages[-1]
    last_message["response"] = user_response
    history_messages[-1] = last_message
    context = [{"role": "assistant", "content": message["question"]} for message in history_messages]
    context.append({"role": "user", "content": user_response})
    result = generate_follow_up_question(context)
    if result['valid']:
        collected_info[result['parameter']] = result['value']
        new_message = WorkflowChatMessage(question=result['next_question'])
        history_messages.append(jsonable_encoder(new_message))
        update_data = {
            "messages": history_messages,
            "collected_info": collected_info
        }
        if result['finished']:
            update_data["is_completed"] = True
            json_filename = save_workflow_chat_to_json(chatId, collected_info)
            update_data["json_filename"] = json_filename
        update_workflow_chat = get_workflow_chat_collection(request).update_one(
            {"_id": chatId},
            {"$set": update_data}
        )
        if update_workflow_chat.modified_count == 0:
            raise HTTPException(status_code=404, detail="Workflow chat not found")
        response = {
            "workFlowChatId": chatId,
            "question": result['next_question'],
        }
        if result['finished']:
            # response["message"] = "Workflow completed. JSON file saved."
            # response["json_filename"] = json_filename
            workFlow = get_workflow_collection(request).find_one({"_id": workFlowId})
            return workFlow
        return response
    else:
        raise HTTPException(status_code=400, detail=result['message'])
    


       
def read_campaign_info(chat_id: str):
    filename = f"campaign_launch_requirements_{chat_id}.json"
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Campaign info JSON file not found")
    
    with open(filename, 'r') as file:
        campaign_info = json.load(file)
    
    return campaign_info

def create_filled_workflow(campaign_info):
    message = f"""
    You are a Dripify campaign launch expert. Your task is to fill out a complete workflow object based on the given campaign information. The workflow object should include all necessary details for launching a campaign in Dripify, including specific actions to perform, their descriptions, and relevant values.

    Campaign information:
    Campaign Type: {campaign_info.get('CampaignType', 'N/A')}
    Campaign Duration: {campaign_info.get('CampaignDuration', 'N/A')}
    Content Type: {campaign_info.get('ContentType', 'N/A')}
    Call To Action: {campaign_info.get('CallToAction', 'N/A')}
    Personalization Level: {campaign_info.get('PersonalizationLevel', 'N/A')}
    A/B Testing Elements: {campaign_info.get('A/BTestingElements', 'N/A')}
    Success Metrics: {campaign_info.get('SuccessMetrics', 'N/A')}

    Please fill out the following workflow object template with appropriate values based on the campaign information:

    {{
      "workFlowName": "Create New Campaign",
      "endGoal": "Boost engagement with a {{CampaignType}} campaign",
      "variables": [
        {{"CampaignType": "{{CampaignType}}"}},
        {{"CampaignDuration": "{{CampaignDuration}}"}},
        {{"ContentType": "{{ContentType}}"}},
        {{"CallToAction": "{{CallToAction}}"}},
        {{"PersonalizationLevel": "{{PersonalizationLevel}}"}},
        {{"A/BTestingElements": "{{A/BTestingElements}}"}},
        {{"SuccessMetrics": "{{SuccessMetrics}}"}}
      ],
      "workFlowServiceName": "Dripify",
      "createdAt": "{{current_utc_time}}",
      "updatedAt": "{{current_utc_time}}",
      "actionsToPerform": [
        {{
          "_id": "f27deb92-5b96-49cd-9c4e-5253308fdd46",
          "actionTitle": "Click on 'Campaigns'",
          "description": "Click on 'Campaigns'",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": "{{CampaignType}}"
          }},
          "elemPath": "//*[@id='campaigns-link']",
          "eleClass": "aside__nav-link, js-ripple",
          "eleId": "campaigns-link",
          "actionType": "user"
        }},
        {{
          "_id": "d77e43e9-b0e0-4ed7-8d79-86ed71317138",
          "actionTitle": "Click on 'New Campaign'",
          "description": "Click on 'New Campaign'",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": ""
          }},
          "elemPath": "/html/body/div[1]/div[1]/main/div[1]/div[1]/span/a/span",
          "eleClass": "",
          "eleId": "",
          "actionType": "user"
        }},
        {{
          "_id": "21cc0553-928c-49ef-a91e-e29669bd04e8",
          "actionTitle": "Click on 'Add Leads'",
          "description": "Click on 'Add Leads'",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": ""
          }},
          "elemPath": "/html/body/div[1]/div[1]/main/div[1]/div/div[2]/div/section/div[2]/button",
          "eleClass": "btn, btn--base",
          "eleId": "",
          "actionType": "user"
        }},
        {{
          "_id": "77896e4e-8af8-4567-9533-d1df007ebe1e",
          "actionTitle": "Click to fill list name",
          "description": "Click to fill list name",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": "Boost engagement with a {{CampaignType}} campaign"
          }},
          "elemPath": "//*[@id='leadsPackName']",
          "eleClass": "field__input",
          "eleId": "leadsPackName",
          "actionType": "user"
        }},
        {{
          "_id": "89ec2bc0-7cc1-467a-b908-74bcd3cca858",
          "actionTitle": "Fill list name",
          "description": "Fill list name",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "type",
            "value": "Boost engagement with a {{CampaignType}} campaign"
          }},
          "elemPath": "//*[@id='leadsPackName']",
          "eleClass": "field__input",
          "eleId": "leadsPackName",
          "actionType": "user"
        }},
        {{
          "_id": "181dddca-141e-4cb1-b196-68bb10211eaf",
          "actionTitle": "Click to fill your saved search.",
          "description": "Click to fill your saved search.",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": ""
          }},
          "elemPath": "//*[@id='LinkedInSearch']",
          "eleClass": "field__input",
          "eleId": "LinkedInSearch",
          "actionType": "user"
        }},
        {{
          "_id": "f381b70a-02ee-4ceb-bd1e-bdb0ae7bdad9",
          "actionTitle": "Fill your saved search.",
          "description": "Fill your saved search.",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "fill",
            "value": "{{CampaignType}}-saved-search-url"
          }},
          "elemPath": "//*[@id='LinkedInSearch']",
          "eleClass": "field__input",
          "eleId": "LinkedInSearch",
          "actionType": "user"
        }},
        {{
          "_id": "a5b1c70a-02ee-4ceb-bd1e-bdb0ae7bdad9",
          "actionTitle": "Click on 'Create a list'",
          "description": "Click on 'Create a list'",
          "toolUrl": "http://example.com",
          "action": {{
            "type": "click",
            "value": ""
          }},
          "elemPath": "//*[@id='main']/section/section/div[3]/button[2]",
          "eleClass": "btn btn--primary btn--xlarge btn--addProspect",
          "eleId": "CreateAList",
          "actionType": "user"
        }}
      ]
    }}

    Please fill in all placeholders ({{placeholder}}) with appropriate values based on the campaign information provided. Ensure that the output is a valid JSON object.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": message}
            ],
            temperature=0.7,
        )

        filled_workflow = json.loads(response['choices'][0]['message']['content'])
        
        # Ensure createdAt and updatedAt are set to the current time
        current_time = datetime.utcnow().isoformat() + "Z"
        filled_workflow['createdAt'] = current_time
        filled_workflow['updatedAt'] = current_time

        return filled_workflow
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

def process_and_save_filled_workflow(chat_id: str):
    campaign_info = read_campaign_info(chat_id)
    filled_workflow = create_filled_workflow(campaign_info)
    
def save_filled_workflow(chat_id: str, filled_workflow: dict):
    filename = f"filled_workflow_{chat_id}.json"
    with open(filename, 'w') as file:
        json.dump(filled_workflow, file, indent=2)
    return filename
