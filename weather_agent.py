import json
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def query_db(sql):
    pass

def run_command(command):
    result = os.system(command=command)
    return result

def get_weather(city: str):
    # TODO!: Do an actual API Call
    print("🔨 Tool Called: get_weather", city)
    
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)
    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    return "Something went wrong"

def add(x, y):
    print("🔨 Tool Called: add", x, y)
    return x + y

available_tools = {
    "get_weather": {
        "fn": get_weather,
        "description": "Takes a city name as an input and returns the current weather for the city"
    },
    "run_command": {
        "fn": run_command,
        "description": "Takes a command as input to execute on system and returns output"
    }
}

system_prompt = f"""
    You are a helpful AI Assistant who is specialized in resolving user queries.
    You work on start, plan, action, observe mode.
    For the given user query and available tools, plan the step by step execution, based on the planning,
    select the relevant tool from the available tool. and based on the tool selection you perform an action to call the tool.
    Wait for the observation and based on the observation from the tool call resolve the user query.
    Rules:
    - Follow the Output JSON Format.
    - Always perform one step at a time and wait for next input
    - Carefully analyze the user query
    Output JSON Format:
    {{
        "step": "string",
        "content": "string",
        "function": "The name of function if the step is action",
        "input": "The input parameter for the function",
    }}
    Available Tools:
    - get_weather: Takes a city name as an input and returns the current weather for the city
    - run_command: Takes a command as input to execute on system and returns output
    
    Example:
    User Query: What is the weather of new york?
    Output: {{ "step": "plan", "content": "The user is interested in weather data of new york" }}
    Output: {{ "step": "plan", "content": "From the available tools I should call get_weather" }}
    Output: {{ "step": "action", "function": "get_weather", "input": "new york" }}
    Output: {{ "step": "observe", "output": "12 Degree Cel" }}
    Output: {{ "step": "output", "content": "The weather for new york seems to be 12 degrees." }}
"""

# Set up the model
generation_config = {
    "response_mime_type": "application/json",
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config
)

# Start the conversation
chat = model.start_chat(history=[
    {"role": "user", "parts": [system_prompt]}
])

# Add a system message to ensure the model understands its role
chat.send_message("I understand the instructions and will follow the STAR pattern using valid JSON format for all responses.")

print("🤖 STAR Agent with Gemini initialized! Type your queries below.")

while True:
    user_query = input('> ')
    if user_query.lower() in ['exit', 'quit', 'bye']:
        print("👋 Goodbye!")
        break
    
    # Send user query to the model
    while True:
        try:
            # Get response from Gemini
            response = chat.send_message(user_query)
            response_text = response.text
            
            # Parse the JSON output
            try:
                parsed_output = json.loads(response_text)
            except json.JSONDecodeError:
                # If the response is not valid JSON, try to extract JSON from the text
                print("⚠️ Invalid JSON response. Trying to fix...")
                import re
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, response_text, re.DOTALL)
                if match:
                    try:
                        parsed_output = json.loads(match.group(0))
                    except:
                        print("❌ Could not parse JSON from response. Retrying...")
                        continue
                else:
                    print("❌ Could not find JSON in response. Retrying...")
                    continue
            
            # Process based on the step
            if parsed_output.get("step") == "plan":
                print(f"🧠: {parsed_output.get('content')}")
                # Send a message to continue processing
                response = chat.send_message("Continue with your planning or move to the next step.")
                continue
            
            if parsed_output.get("step") == "action":
                tool_name = parsed_output.get("function")
                tool_input = parsed_output.get("input")
                
                if tool_name in available_tools:
                    # Execute the tool
                    if tool_name == "get_weather":
                        output = available_tools[tool_name]["fn"](tool_input)
                    elif tool_name == "run_command":
                        output = available_tools[tool_name]["fn"](tool_input)
                    else:
                        output = "Tool not implemented yet"
                    
                    # Send observation back to the model
                    observation_msg = json.dumps({"step": "observe", "output": output})
                    print(f"👁️: {output}")
                    response = chat.send_message(observation_msg)
                    continue
                else:
                    print(f"❌ Tool {tool_name} not available.")
                    response = chat.send_message("The tool you requested is not available. Please try another approach.")
                    continue
            
            if parsed_output.get("step") == "output":
                print(f"🤖: {parsed_output.get('content')}")
                break
            
            # If we get an unexpected step type, inform the model and try again
            response = chat.send_message("Please follow the STAR pattern with valid step types (plan, action, observe, output).")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break