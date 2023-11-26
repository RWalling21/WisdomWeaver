from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
import json

# Set OpenAI API Key 
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

#Prompts
from .prompt import educate_prompt, summary_prompt, search_prompt

# WebScraping methods 
from .scrape import web_searcher, scrape_text

# Given a list_of_lists collapse into a single list
def collapse_list_of_lists(list_of_lists):
    content = []
    for l in list_of_lists:
        content.append("\n\n".join(l))
    return "\n\n".join(content)

# Chain definitions
# Chain to scrape page data and summarize using a ChaptGPT Model
scrape_and_summarize_chain = RunnablePassthrough.assign(
    # Summary is the chain below
    summary=RunnablePassthrough.assign(
    # Scrape the first 10000 lines of text from the given url.
    text=lambda page_content: (page_content, scrape_text(page_content["url"]))[1][:10000]
) | summary_prompt | ChatOpenAI(model="gpt-3.5-turbo-1106") | StrOutputParser() 
# Adding the URL to the context makes it easier for the model to cite sources 
) | (lambda input: f"URL: {input['url']}\n\nSUMMARY: {input['summary']}") 

# Chain to search for external information using user input
web_search_chain = RunnablePassthrough.assign(
    urls = lambda input: web_searcher(input["question"])
) | (lambda input: [{"question": input["question"], "url": u} for u in input["urls"]]) | scrape_and_summarize_chain.map()

# Chain to generate search queries for the given question
search_question_chain = search_prompt | ChatOpenAI(temperature=1) | StrOutputParser() | (lambda response: json.loads(response))

# Researches given topic and summarizes based off results 
research_chain = search_question_chain | (lambda input: [{"question": q} for q in input]) | web_search_chain.map()

# Main chain 
chain = RunnablePassthrough.assign(
    search_summary= research_chain | collapse_list_of_lists
) | educate_prompt | ChatOpenAI(model="gpt-3.5-turbo-1106") | StrOutputParser() 
