# Use the official Python base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app
RUN git clone https://github.com/arcee-ai/mergekit.git && cd mergekit && pip install -e . && cd ..
# Copy the current directory contents into the container at /app
COPY . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN mkdir /app/YAML_FILES
# Expose the default Jupyter Notebook port
EXPOSE 8888

# Map a volume for data
VOLUME /app

# Start Jupyter Notebook when the container launches
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8888"]