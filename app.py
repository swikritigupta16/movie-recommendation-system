import os
import gdown
import pickle
import streamlit as st
import requests
import pandas as pd
from difflib import get_close_matches

# --------------------------------
# Step 1: Download required pickle files from Google Drive if not present
# --------------------------------
SIMILARITY_URL = "https://drive.google.com/uc?id=1h4WadszQ-tDJ58WMAtLyjx5VBEDG9MUW"
MOVIEDICT_URL = "https://drive.google.com/uc?id=1-G5dhA3xDLllJ4DkO3OcVkDip5wLZNYx"

if not os.path.exists("similarity.pkl"):
    st.warning("Downloading similarity.pkl from Google Drive...")
    gdown.download(SIMILARITY_URL, "similarity.pkl", quiet=False)

if not os.path.exists("movie_list.pkl"):
    st.warning("Downloading movie_list.pkl from Google Drive...")
    gdown.download(MOVIEDICT_URL, "movie_list.pkl", quiet=False)

# --------------------------------
# Step 2: Load the pickled data
# --------------------------------
movies_dict = pickle.load(open('movie_list.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)

# --------------------------------
# Step 3: Helper to fetch movie poster using TMDB API
# --------------------------------
API_KEY = "d472196d5f46e89705c43c918003a591"

def fetch_poster(movie_id, fallback_title=None):
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except:
        pass
    
    if fallback_title:
        try:
            search_response = requests.get(
                f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={fallback_title}",
                timeout=10
            )
            search_response.raise_for_status()
            results = search_response.json().get('results')
            if results and results[0].get('poster_path'):
                return f"https://image.tmdb.org/t/p/w500/{results[0]['poster_path']}"
        except:
            pass

    return "https://via.placeholder.com/500x750?text=No+Poster"

# --------------------------------
# Step 4: Recommendation logic
# --------------------------------
def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommended_posters = []

    for i in movies_list:
        title = movies.iloc[i[0]].title
        movie_id = movies.iloc[i[0]].movie_id
        recommended_movies.append(title)
        recommended_posters.append(fetch_poster(movie_id, fallback_title=title))

    return recommended_movies, recommended_posters

# --------------------------------
# Step 5: Streamlit UI - Main Content
# --------------------------------
st.title('🎬 Movie Recommendation System')

selected_movie_name = st.selectbox("What would you like to watch?", movies['title'].values)

if st.button('Recommend'):
    names, posters = recommend(selected_movie_name)
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            st.text(names[i])
            st.image(posters[i])

# --------------------------------
# Step 6: Streamlit UI - Chatbot Sidebar
# --------------------------------
st.sidebar.title("💬 Movie Bot")

if 'messages' not in st.session_state:
    st.session_state.messages = []

def chatbot_response(user_message):
    def extract_movie_title(msg):
        return msg.lower().split("like", 1)[-1].strip() if "like" in msg.lower() else msg.strip()

    if 'recommend' in user_message.lower():
        movie_query = extract_movie_title(user_message)
        normalized_titles = movies['title'].str.lower().tolist()
        closest_match = get_close_matches(movie_query, normalized_titles, n=1, cutoff=0.6)

        if closest_match:
            original_title = movies[movies['title'].str.lower() == closest_match[0]]['title'].values[0]
            recommended_movies, _ = recommend(original_title)
            return f"I recommend: {', '.join(recommended_movies)}"
        else:
            return "❌ Sorry, I couldn't find that movie. Try another title!"
    return "🤖 I can recommend movies! Try asking: *Recommend me a movie like Inception.*"

user_message = st.sidebar.text_input("Type your message here:")

if st.sidebar.button("Send"):
    if user_message:
        st.session_state.messages.append(("You", user_message))
        bot_response = chatbot_response(user_message)
        st.session_state.messages.append(("Bot", bot_response))

for sender, message in st.session_state.messages:
    st.sidebar.markdown(f"**{sender}:** {message}")
