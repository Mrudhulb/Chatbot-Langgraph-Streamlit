# 🤖 Streamlit LangGraph Chatbot

This project is a web-based chatbot application built with Streamlit and [suspicious link removed]. It uses Google's Gemini model via langchain-google-genai to power the conversation and features a built-in memory system that automatically summarizes the conversation to manage context length.

## Features

**Interactive Chat UI:** A clean, responsive chat interface provided by Streamlit.

**Persistent Memory:** Uses LangGraph's MemorySaver to maintain conversation history for each user session (identified by a unique thread_id).

**Stateful Conversation Flow:** Built with LangGraph's StateGraph to manage the conversation state.

**Auto-Summarization:** After 6 messages, the graph automatically triggers a summarization step to condense the history, sending the summary back to the model as context for future turns.

**Google Gemini Model:** Leverages the gemini-2.5-flash model for fast and capable chat responses.

## Requirements

### Python

Python 3.13 (Note: This project is built for Python 3.13. Using other versions, like 3.14, may cause dependency issues with packages like pyarrow during streamlit installation).

### Google API Key

* This application requires a Google API key to use the Gemini model.

* Go to [Google AI Studio](https://aistudio.google.com/app/api-keys)

* Sign in with your Google account.

* Click on "Create API key" to get your key.

* Copy this key. You will need it for both local and cloud deployment.

# 🚀 Setup & Deployment

You can deploy this application in two ways: directly to Streamlit Community Cloud or by running it locally on your desktop.



## Option 1:
### Deploying on Streamlit Community Cloud (Recommended)

* This is the easiest way to deploy and share your app. It deploys directly from your GitHub account.

* Fork this Repository: Click the "Fork" button at the top-right of this page to create your own copy of this project in your GitHub account.

* Sign up for Streamlit: Go to Streamlit Community Cloud and sign in with your GitHub account.

### Deploy New App:

* On your Streamlit dashboard, click "New app".

* Select your forked repository.

* Choose the branch.

* Ensure the main file path is set to app.py.

* Click "Advanced settings...".

### Add Your Secret Key:

* In the "Secrets" section, paste your Google API key (from the prerequisite step) in this format:

*GOOGLE_API_KEY="YOUR_API_KEY_HERE"*


* Deploy! Click the "Deploy!" button. Streamlit will handle installing the requirements and launching your app.

## Option 2: 
### Running Locally on Your Desktop

* Follow these steps to set up and run the chatbot on your local machine.

### Clone the Repository

* First, clone the repository (either the original or your fork) to your local machine.

  *git clone https://github.com/Mrudhulb/Chatbot-Langgraph-Streamlit<t>*

  or

  *git clone <forked-repository-url<t>>*

  *cd <repository-name<t>>*


### Create the environment
* It's highly recommended to use a virtual environment. Make sure you have installed Python 3.13.
  * **On macOS/Linux:**
    *python3.13 -m venv venv*
  * **On Windows:**
    *py -3.13 -m venv venv*
### Activate the environment
* **On macOS/Linux:**
  *source venv/bin/activate*
* **On Windows:**
  *.\venv\Scripts\activate*


### Install Dependencies

* Install all the required packages from the requirements.txt file.

  *pip install -r requirements.txt*


### Set Up Environment Variables

* Add your **Google API key** (from the prerequisite step) to the .env file:

  *GOOGLE_API_KEY="YOUR_API_KEY_HERE"*


### Run the Application

* Once your dependencies are installed and your API key is set, run the Streamlit app.

  *streamlit run app.py*


* Your browser should automatically open to the chatbot interface, ready for you to start chatting!
