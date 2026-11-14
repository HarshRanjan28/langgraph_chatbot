import streamlit as st
from langchain_core.messages import HumanMessage
from backend import chatbot,thread_id
import uuid

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def load_conversation(thread_id):
    state = chatbot.get_state(
        config={"configurable": {"thread_id": str(thread_id)}}
    )
    return state.values.get('messages', [])

########################### Sidebar UI ###########################
st.sidebar.title("Langgraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.title("My Conversations")

st.sidebar.title(st.session_state['thread_id'])

for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            if isinstance(msg,HumanMessage):
                role = "user"
            else:
                role = "ai"
            temp_messages.append({"role":role,"content":msg.content})
        st.session_state['message_history'] = temp_messages

add_thread(st.session_state['thread_id'])

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

CONFIG = {
    "configurable": {
        "thread_id": str(st.session_state['thread_id'])
    }
}

user_input = st.chat_input("Type here")

if user_input:
    st.session_state['message_history'].append({"role":"user",'content':user_input})
    with st.chat_message("user"):
        st.text(user_input)

    with st.chat_message("ai"):
        ai_message = st.write_stream(
            message_chunk.content for message_chunk,metadata in chatbot.stream(
                {'messages':[HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )
    st.session_state['message_history'].append({"role":"ai","content":ai_message})
