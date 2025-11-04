FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY keyboard_smashers/ ./keyboard_smashers/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "keyboard_smashers.api:app", "--host", "0.0.0.0", "--port", "8000"]
# http://localhost:8000
# http://localhost:8000/docs 
# uvicorn keyboard_smashers.api:app --reload --host 0.0.0.0 --port 8000

#to recreate docker to use new updated code
# docker stop keyboard-smashers-api
# docker rm keyboard-smashers-api
# docker build -t keyboard-smashers-api .
# docker run -d -p 8000:8000 -v ${PWD}/data:/app/data --name keyboard-smashers-api --restart unless-stopped keyboard-smashers-api

#how to push
#git add .
#git status
#git commit -m "your message"
#git push // git push --set-upstream origin dev 

#.\venv\Scripts\activate to get enviromment
#cntl+shift+p select interpret select venv

#To test main "python -m keyboard_smashers.main"