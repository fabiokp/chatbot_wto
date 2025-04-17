__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain import hub

# Initialize LLM
llm = init_chat_model("gpt-4.1-mini-2025-04-14", model_provider="openai")
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


# Load vector store
vector_store = Chroma(
    collection_name="wto_texts",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db"
)

# Create retriever
retriever = vector_store.as_retriever()

# Load a pre-defined prompt from the LangChain hub
wto_assistant_prompt = (
    "You are a legal counsel specialized in international law, assisting government "
    "officials on the subject of the World Trade Organization's official documents and annexes."
    "Keep your answers legally rigorous and precise in terminology."
    "Be specific and close to the textual content of the documents. Try to name the articles and annexes, and paraphrase them whenever possible."
    "If necessary, add a few bullet points to summarise at the end. \n"
    "Question: {question} \n"
    "Context: {context} \n"
    "Answer:"
)

prompt_template = hub.pull("rlm/rag-prompt").from_messages([wto_assistant_prompt])

# Configuração do aplicativo Streamlit
st.set_page_config(page_title="ChatOMC", 
                   page_icon="🌐", 
                   layout="centered"  # Use centered layout for a more focused chat interface
                   )
st.title("🌐 ChatOMC")
st.markdown(
    """
    Bem-vindo ao ChatOMC.
    Esta ferramenta especializada auxilia na consulta e interpretação dos acordos e documentos oficiais da Organização Mundial do Comércio.     
    Formule sua pergunta para iniciar a análise.

    <span style='color:grey; font-style: italic;'>Exemplos de perguntas:</span>
    <ul>
        <li><span style='color:grey; font-style: italic;'>Quais documentos compõem o núcleo do arcabouço normativo da OMC?</span></li>
        <li><span style='color:grey; font-style: italic;'>Como se diferencia o tratamento dado ao comércio de serviços em relação ao comércio de bens?</span></li>
        <li><span style='color:grey; font-style: italic;'>Quais as disposições que tratam da proteção intelectual de circuitos integrados?</span></li>
        <li><span style='color:grey; font-style: italic;'>Quais são as condições necessárias para a aplicação de uma medida anti-dumping?</span></li>
        <li><span style='color:grey; font-style: italic;'>Como contestar uma medida anti-dumping aplicada por um terceiro país?</span></li>
    </ul>
    """,
    unsafe_allow_html=True
)

# Inicializar o estado da sessão para o histórico de conversas
if "history" not in st.session_state:
    st.session_state.history = []

# Exibir o histórico de conversas usando st.chat_message
for speaker, message in st.session_state.history:
    role = "user" if speaker == "Você" else "assistant"
    with st.chat_message(role):
        st.markdown(message)

# Placeholder para mensagens temporárias (pode be removed if not needed with chat_input)
# status_placeholder = st.empty() # Consider removing if chat_input handles loading state implicitly

# Processar a entrada do usuário e gerar resposta
if user_input := st.chat_input("Qual sua dúvida?"):
    # Adicionar a entrada do usuário ao histórico de conversas
    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner(":books: Buscando resposta nos documentos oficiais..."):
        # Format chat history for context
        history_context = "\n".join([f"{speaker}: {message}" for speaker, message in st.session_state.history])

        # Recuperar documentos relevantes
        retrieved_docs = retriever.invoke(user_input)
        document_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        # Extract unique source links from metadata
        sources = set() # Use a set to store unique links
        if retrieved_docs:
            for doc in retrieved_docs:
                if doc.metadata:
                    link = doc.metadata.get('link') # Assuming 'link' holds the URL
                    # Ensure link is present and a non-empty string
                    if link and isinstance(link, str) and link.strip():
                        sources.add(link.strip())

        # Combine history and document context
        combined_context = f"Conversation History:\n{history_context}\n\nRetrieved Documents:\n{document_context}"

        # Gerar resposta usando o prompt com o contexto combinado
        example_messages = prompt_template.invoke(
            {"context": combined_context, "question": user_input}
        ).to_messages()

        response = llm.invoke(example_messages)
        assistant_response_content = response.content

        # Append sources to the response content if any were found
        if sources:
            # Format sources as a simple list of links
            sources_text = "\n\n**Fontes:**\n" + "\n".join(f"- {link}" for link in sorted(list(sources)))
            assistant_response_content += sources_text
        # else: # Optionally add a message if no sources are found
        #     assistant_response_content += "\n\n(Nenhuma fonte específica identificada no contexto recuperado)"

        # Adicionar a resposta do modelo ao histórico de conversas
        # Display assistant message with sources
        with st.chat_message("assistant"):
            st.markdown(assistant_response_content) # Display content with sources

        # Update history after displaying messages
        st.session_state.history.append(("Você", user_input))
        # Store the response *with* sources in history
        st.session_state.history.append(("Assistente OMC", assistant_response_content))
