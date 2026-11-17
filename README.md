# SalatFarm-AI-Assistent
Testenvironment for a local LLM Agent, using Pydantic, Ollama and a simple Verticalfarm Model in Modelica.

-------------------------------------------------------------------
How to Install and Start:
1. Install Ollama and use a local LLM of your choice; so far only tested with qwen3:4b

2. Start your Python evironment and go to the directory of files provided: for example "cd C:\Users\xxxx\Desktop\VerticalFarming"

3. Execute: "python -m streamlit run streamlit_app.py"

4. Start ollama and execute: "ollama run qwen3:4b"

5. Use the Streamlit Interface to interact with Assistent! 

Tested with Nvidia Geforce GTX970 and 4gb of VRAM -> only qwen 2.5:3b runs fast. 

In local_agent you can adjust the model used.

Latest updates:

Implemented a visualization tool that allows the user to request a plot of: plantmass, water consumption, energy, illumination etc.

Providing previous chat to allow follow-up questions -> Problem: increased context requieres more VRAM and a restart after longer conversations
