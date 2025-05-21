import random
from models import Quiz

def generate_recommendations_for_user(user, num_recommendations=3):
    """
    Generate book recommendations based on user's quiz history
    
    Args:
        user: The user object
        num_recommendations: Number of recommendations to generate
        
    Returns:
        list: List of book recommendation dictionaries
    """
    # Get the user's completed quizzes
    quizzes = Quiz.query.filter_by(user_id=user.id, is_completed=True).all()
    
    # Extract topics and genres from quizzes
    topics = []
    for quiz in quizzes:
        topics.append({
            'topic': quiz.topic,
            'topic_type': quiz.topic_type,
            'score': quiz.score
        })
    
    # If user has no quiz history, return generic recommendations
    if not topics:
        return get_generic_recommendations(num_recommendations)
    
    # Group by topic and get average score
    topic_scores = {}
    for topic in topics:
        key = f"{topic['topic']}|{topic['topic_type']}"
        if key not in topic_scores:
            topic_scores[key] = {'count': 0, 'total_score': 0}
        
        topic_scores[key]['count'] += 1
        topic_scores[key]['total_score'] += topic['score']
    
    # Calculate average scores
    for key in topic_scores:
        topic_scores[key]['avg_score'] = topic_scores[key]['total_score'] / topic_scores[key]['count']
    
    # Sort by average score (highest first)
    sorted_topics = sorted(
        [(k.split('|')[0], k.split('|')[1], v['avg_score']) for k, v in topic_scores.items()],
        key=lambda x: x[2],
        reverse=True
    )
    
    # Use the top topics to generate recommendations
    recommendations = []
    
    for topic, topic_type, score in sorted_topics[:num_recommendations]:
        # Get similar books/authors based on the high-scoring topics
        similar_items = get_similar_items(topic, topic_type)
        if similar_items:
            recommendations.extend(similar_items)
    
    # If we still need more recommendations
    if len(recommendations) < num_recommendations:
        recommendations.extend(get_generic_recommendations(num_recommendations - len(recommendations)))
    
    # Deduplicate and limit
    unique_recommendations = []
    recommendation_titles = set()
    
    for rec in recommendations:
        if rec['title'] not in recommendation_titles:
            unique_recommendations.append(rec)
            recommendation_titles.add(rec['title'])
        
        if len(unique_recommendations) >= num_recommendations:
            break
    
    return unique_recommendations

def get_similar_items(topic, topic_type):
    """
    Get items similar to the given topic
    
    Args:
        topic: Book title or author name
        topic_type: 'book' or 'author'
        
    Returns:
        list: List of similar items
    """
    # This is a simplified version. In a real application, you would:
    # 1. Use a recommendation API or algorithm
    # 2. Query a database of books/authors
    # 3. Use a content-based filtering approach
    
    # For now, we'll use hardcoded recommendations based on popular genres
    
    # Classic literature recommendations
    if any(word in topic.lower() for word in ['austen', 'pride', 'prejudice', 'sense', 'emma', 'persuasion']):
        return [
            {
                'title': 'Jane Eyre',
                'author': 'Charlotte Brontë',
                'reason': 'Classic literature with strong female protagonists'
            },
            {
                'title': 'Wuthering Heights',
                'author': 'Emily Brontë',
                'reason': 'Gothic romance in classic British literature'
            }
        ]
    
    # Fantasy recommendations
    elif any(word in topic.lower() for word in ['potter', 'rowling', 'hogwarts', 'wizard', 'tolkien', 'ring', 'hobbit']):
        return [
            {
                'title': 'The Name of the Wind',
                'author': 'Patrick Rothfuss',
                'reason': 'Magical fantasy with a school of magic'
            },
            {
                'title': 'A Wizard of Earthsea',
                'author': 'Ursula K. Le Guin',
                'reason': 'Classic fantasy about a young wizard'
            }
        ]
    
    # Science fiction recommendations
    elif any(word in topic.lower() for word in ['asimov', 'foundation', 'robot', 'dune', 'herbert', 'sci-fi', 'science fiction']):
        return [
            {
                'title': 'The Left Hand of Darkness',
                'author': 'Ursula K. Le Guin',
                'reason': 'Thought-provoking science fiction'
            },
            {
                'title': 'Hyperion',
                'author': 'Dan Simmons',
                'reason': 'Epic space opera with complex world-building'
            }
        ]
    
    # Mystery/thriller recommendations
    elif any(word in topic.lower() for word in ['christie', 'poirot', 'marple', 'murder', 'mystery', 'detective', 'sherlock', 'holmes']):
        return [
            {
                'title': 'The Girl with the Dragon Tattoo',
                'author': 'Stieg Larsson',
                'reason': 'Modern mystery thriller with complex characters'
            },
            {
                'title': 'In the Woods',
                'author': 'Tana French',
                'reason': 'Psychological mystery with literary depth'
            }
        ]
    
    # Dystopian recommendations
    elif any(word in topic.lower() for word in ['orwell', '1984', 'dystopian', 'dystopia', 'brave new world', 'huxley', 'hunger games']):
        return [
            {
                'title': 'The Handmaid\'s Tale',
                'author': 'Margaret Atwood',
                'reason': 'Dystopian fiction with social commentary'
            },
            {
                'title': 'Station Eleven',
                'author': 'Emily St. John Mandel',
                'reason': 'Post-apocalyptic literary fiction'
            }
        ]
    
    # Return empty list if no matches
    return []

def get_generic_recommendations(count):
    """
    Get generic recommendations for users without quiz history
    
    Args:
        count: Number of recommendations to return
        
    Returns:
        list: List of recommendation dictionaries
    """
    recommendations = [
        {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'reason': 'Classic American literature with important social themes'
        },
        {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'reason': 'A masterpiece of American literature'
        },
        {
            'title': '1984',
            'author': 'George Orwell',
            'reason': 'Influential dystopian fiction'
        },
        {
            'title': 'Pride and Prejudice',
            'author': 'Jane Austen',
            'reason': 'Classic romance with witty social commentary'
        },
        {
            'title': 'The Hobbit',
            'author': 'J.R.R. Tolkien',
            'reason': 'Beloved fantasy adventure'
        },
        {
            'title': 'Harry Potter and the Philosopher\'s Stone',
            'author': 'J.K. Rowling',
            'reason': 'Modern fantasy classic'
        },
        {
            'title': 'The Alchemist',
            'author': 'Paulo Coelho',
            'reason': 'Inspirational philosophical fiction'
        },
        {
            'title': 'The Hunger Games',
            'author': 'Suzanne Collins',
            'reason': 'Gripping dystopian YA fiction'
        }
    ]
    
    # Shuffle and limit to requested count
    random.shuffle(recommendations)
    return recommendations[:count]
