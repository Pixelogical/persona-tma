from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# First API call with reasoning
response = client.chat.completions.create(
  model="nvidia/nemotron-3-ultra-550b-a55b:free",
  messages=[
          {
            "role": "user",
            "content": "How many r's are in the word 'strawberry'?"
          }
        ],
  extra_body={"reasoning": {"enabled": True}}
)

# Extract the assistant message with reasoning_details
response = response.choices[0].message

    irint(POST_ID)
# Preserve the assistant message with reasoning_details
messages = [
  {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
  {
    "role": "assistant",
    "content": response.content,
    "reasoning_details": response.reasoning_details  # Pass back unmodified
  },
  {"role": "user", "content": "Are you sure? Think carefully."}
]

# Second API call - model continues reasoning from where it left off
response2 = client.chat.completions.create(
  model="nvidia/nemotron-3-ultra-550b-a55b:free",
  messages=messages,
  extra_body={"reasoning": {"enabled": True}}
)
