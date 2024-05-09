from huggingface_hub import ModelCard
from huggingface_hub import HfApi
from jinja2 import Template
import yaml
import os

def generate_cards(merge_dir: str, yaml_config: str):
    # !pip install -qU huggingface_hub

    template_text = """
    ---
    license: apache-2.0
    tags:
    - merge
    - mergekit
    - lazymergekit
    {%- for model in models %}
    - {{ model }}
    {%- endfor %}
    ---

    # {{ model_name }}

    {{ model_name }} is a merge of the following models using [mergekit](https://github.com/cg123/mergekit):

    {%- for model in models %}
    * [{{ model }}](https://huggingface.co/{{ model }})
    {%- endfor %}

    ## 🧩 Configuration

    \```yaml
    {{- yaml_config -}}
    \```
    """

    # Create a Jinja template object
    jinja_template = Template(template_text.strip())

    # Get list of models from config
    # Read YAML data from file
    with open(yaml_config, 'r', encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if "models" in data:
        models = [data["models"][i]["model"] for i in range(len(data["models"])) if "parameters" in data["models"][i]]
    elif "parameters" in data:
        models = [data["slices"][0]["sources"][i]["model"] for i in range(len(data["slices"][0]["sources"]))]
    elif "slices" in data:
        models = [data["slices"][i]["sources"][0]["model"] for i in range(len(data["slices"]))]
    else:
        raise Exception("No models or slices found in yaml config")

    # Fill the template
    content = jinja_template.render(
        model_name=data["MODEL_NAME"] if "MODEL_NAME" in data else data["models"][0]["model"],
        models=models,
        yaml_config=yaml_config,
        username=data["user_name"] if "user_name" in data else "nguyennhan1992",
    )

    # Save the model card
    card = ModelCard(content)
    card.save(f'{merge_dir}/README.md')

def upload_model(merge_dir: str, yaml_config: str):
    # !pip install -qU huggingface_hub
    with open(yaml_config, 'r', encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Defined in the secrets tab in Google Colab
    api = HfApi(token=os.getenv("HF_TOKEN"))

    api.create_repo(
        repo_id=f"{data['user_name']}/{data['MODEL_NAME'] if 'MODEL_NAME'in data else data['models'][0]['model']}",
        repo_type="model"
    )
    api.upload_folder(
        repo_id=f"{data['user_name']}/{data['MODEL_NAME'] if 'MODEL_NAME' in data else data['models'][0]['model']}",
        folder_path=merge_dir,
    )