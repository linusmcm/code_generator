import os
from dotenv import load_dotenv
import openai
os.environ["OPENAI_API_KEY"] = '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'
import re
import json
from streamlit import session_state as session
import streamlit as st
from streamlit_chat import message

from langchain.llms import OpenAI
from langchain import PromptTemplate
from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
#from langchain.chat_models import ChatOpenAI
#from langchain.chains import ConversationChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from typing import List

# TODO
# from dotenv import load_dotenv, dotenv_values
# load_dotenv()
# config = dotenv_values(".env")
# print(config)
# openai.api_key = config("OPENAI_API_KEY")

openai.api_key = os.environ["OPENAI_API_KEY"]
language_list = ['Python', 'PySpark', 'SQL', 'JavaScript', "Rust", "R Programming", "Java", "Scala"]
model_types = ["gpt-3.5-turbo" ,"gpt-3.5-turbo-0301" ,"text-davinci-003","text-davinci-002","code-davinci-002","gpt-4" ,"gpt-4-0314" ,"gpt-4-32k" ,"gpt-4-32k-0314" ,]
## ----------------------------------------------------------------------------------- ##
# Define LLM Answer Structure
## ----------------------------------------------------------------------------------- ##
class Code_Request(BaseModel):
    generated_code: str = Field(description="the requested programming code answer")
    code_description: str = Field(description="the description of the programming code for documentation purposes")

class Unit_Test_Request(BaseModel):
    unit_test_code: str = Field(description="using the most popular testing package or framework in the specified programming language. Create unit testing programming code with a set sample testing data that can be read into the function to validate the code")
    code_description: str = Field(description="the description of the programming code for documentation purposes")
## ----------------------------------------------------------------------------------- ##
# Prompt templates
## ----------------------------------------------------------------------------------- ##
code_parser = PydanticOutputParser(pydantic_object=Code_Request)
unit_test_parser = PydanticOutputParser(pydantic_object=Unit_Test_Request)


function_prompt = PromptTemplate(
    template="Answer the user query in the following format {format_instructions}. As an expert {language} programmer write a function that has {inputs} as input values and returns a {return_value} data type. This function will {function_description}",
    input_variables=["language", "inputs", 'return_value', 'function_description'],
    partial_variables={"format_instructions": code_parser.get_format_instructions()})


statement_prompt = PromptTemplate(
    template="Answer the user query in the following format {format_instructions}. As an expert {language} programmer write a {language} statement that {function_description}",
    input_variables=["language",'function_description'],
    partial_variables={"format_instructions": code_parser.get_format_instructions()})


unit_test_prompt = PromptTemplate(
    template="Answer the user query in the following format {format_instructions}. As an expert {language} programmer write set of unit tests for the {language} function \n {function_description}. Create a set of data within the scope of the program file that can be used to run and validate the unit tests as an input into the test function",
    input_variables=["language",'function_description'],
    partial_variables={"format_instructions": unit_test_parser.get_format_instructions()})


## ----------------------------------------------------------------------------------- ##
# Streamlit UI
## ----------------------------------------------------------------------------------- ##
st.set_page_config(layout ='wide', page_title="LangChain Demo")
input_session =''

if "return_value_input" not in session: session["return_value_input"] = []
if "function_input" not in session: session["function_input"] = []
if "language_input" not in session: session["language_input"] = []
if "description_input" not in session: session["description_input"] = []
if "output" not in session: session["output"] = []
if "model_temperature" not in session: session["model_temperature"] = 0.3
if "model_types_input" not in session: session["model_types_input"] = []
if "visibility_string" not in session: session["visibility_string"] = 'visible'
if "radio_string" not in session: session["radio_string"] = ''
if "disabled" not in session: session["disabled"] = False
if "debug_radio_string" not in session: session["debug_radio_string"] = ''
if "optimise_output" not in session: session["optimise_output"] = ''
if "load_radio_string" not in session: session["load_radio_string"] = ''


with st.sidebar:
    st.selectbox("Model Selection", model_types, key="model_types_input")
    st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1, key="model_temperature")
    st.selectbox("Programming Language", language_list, key = "language_input")

CodeGenerator_OS, CodeGenerator_chain, Code_Optimisation, Code_Debugging, Unit_Testing, Code_Documentation = st.tabs(["Code Generator - One Shot", "Code Generator - Chain", "Code Optimisation", "Code Debugging", "Unit Testing", "Code Documentation"])
with CodeGenerator_OS:
    build_input_column, ouput_results_column = st.columns([2,3], gap='small')
    with build_input_column:
        st.header("Code Generator - One Shot")
        st.radio("Do you require a Function or a Statement", ("Function", "Statement"),index = 0, key="radio_string")
        if session.radio_string == "Function":
            st.text_input('Function Inputs',value="", key='function_input')
        st.text_area(f'{session.radio_string} Description', value='', key='description_input', height= 175)
        if session.radio_string == "Function":
            st.text_input('Function Return Value', value="", key='return_value_input')
        submit_button = st.button(label='Submit', type ="primary")
        if submit_button:
            if session.radio_string == "Function":
                _input = function_prompt.format_prompt(language=session.language_input
                                            , inputs=session.function_input
                                            , return_value=session.return_value_input
                                            , function_description=session.description_input)
            else:
                _input = statement_prompt.format_prompt(language=session.language_input, function_description=session.description_input)
            model = OpenAI(model_name=session.model_types_input, temperature=session.model_temperature)
            session.output = model(_input.to_string())
    with ouput_results_column:
        if(len(session.output) > 0):
            #st.write(session.output)
            st.subheader("Code Generation")
            output_session = json.loads(session.output)
            st.code(output_session['generated_code'])
            st.subheader("Documentation")
            st.markdown(output_session['code_description'])

with Unit_Testing:
    build_input_column, ouput_results_column = st.columns([2,3], gap='small')
    with build_input_column:
        st.header("Code Unit Test")
        st.radio("Do you require to load a file or a function for Unit Testing?", ("File Load", "Function"), index = 0, key="load_radio_string")
        if session.load_radio_string == "File Load":
            uploaded_files = st.file_uploader(f"Choose a {session.language_input} file", accept_multiple_files=True)
            for uploaded_file in uploaded_files:
                bytes_data = uploaded_file.read()
                st.write("filename:", uploaded_file.name)
                st.code(bytes_data)
        else:
            st.text_area(f'{session.load_radio_string} Code', value='', key='debug_description_input', height= 250)
        submit_optimise = st.button(label=f'Submit {session.load_radio_string}', type ="primary")
        if submit_optimise:
            if session.load_radio_string == "Unit Test":
                input_session = unit_test_prompt.format_prompt(language=session.language_input, function_description=session.debug_description_input)
        model = OpenAI(model_name=session.model_types_input, temperature=session.model_temperature)
        optimise_output = model(input_session.to_string())
        print(optimise_output)
        st.subheader(f"{session.debug_radio_string}")
        st.code(optimise_output)
        st.write(optimise_output)



    with statement_build:
        st.write("statement_build - pending")
