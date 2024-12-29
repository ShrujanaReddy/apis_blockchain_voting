# from sentence_transformers import SentenceTransformer
# import joblib
# import numpy as np

# emb_model = SentenceTransformer("all-MiniLM-L6-v2")
# model = joblib.load('lr_model.joblib')

# def predict_sentiment(text):
#     text_emb = emb_model.encode(text)
#     prediction = model.predict([text_emb])[0]
#     prob = model.predict_proba([text_emb])[0]
#     return prediction,round(np.max(prob),3)

# if __name__ == "__main__":
#     text = 'i dont like this party it should not win'
#     print(predict_sentiment(text))
from transformers import pipeline
import numpy as np

# Initialize the sentiment analysis pipeline with a pre-trained model
sentiment_model = pipeline("sentiment-analysis")

def predict_sentiment(text):
    # Predict sentiment using the transformer model
    result = sentiment_model(text)[0]
    label = result['label']
    score = result['score']

    # Map the sentiment label to human-readable format
    sentiment = 'positive' if label == 'POSITIVE' else 'negative'
    
    # Return sentiment and probability rounded to 3 decimal places
    return sentiment, round(score, 3)

if __name__ == "__main__":
    # Example text
    text = "I don't like this party, it should not win"
    sentiment, probability = predict_sentiment(text)
    print(f"Sentiment: {sentiment}, Probability: {probability}")
