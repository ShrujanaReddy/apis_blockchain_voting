# app.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, ForeignKey, TIMESTAMP, DateTime , text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ConfigDict
from typing import List, Dict
from datetime import datetime
import sentiment
import uuid

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:shrujana@localhost/voter"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
secret_token = uuid.uuid4().hex
with open("secret_token.txt",'w') as fp:
    fp.write(secret_token)
    
# Database Models
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    wallet_address = Column(String, nullable=False)
    is_approved = Column(Boolean, default=False)

class Candidate(Base):
    __tablename__ = "candidates"
    candidate_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    edu_background = Column(String, nullable=False)
    criminal_cases = Column(String, nullable=False)
    goals = Column(String, nullable=False)
    motive = Column(String, nullable=False)
    plan_of_action = Column(String, nullable=False)
    slogan = Column(String, nullable=False)

class Comment(Base):
    __tablename__ = "comments"
    comment_id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.user_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String, nullable=False)
    comment = Column(String, nullable=False)
    sentiment = Column(String, nullable=False)
    sentiment_probability = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

Base.metadata.create_all(bind=engine)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int 
    name: str
    email: str
    wallet_address: str

# Pydantic Models
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: str
    wallet_address: str

class ApproveUser(BaseModel):
    pass  # No request body needed

class CandidateCampaign(BaseModel):
    age: int
    gender: str
    edu_background: str
    criminal_cases: str
    goals: str
    motive: str
    plan_of_action: str
    slogan: str

class CampaignResponse(BaseModel):
    candidate_id: int
    name: str
    campaign: CandidateCampaign

class CommentRequest(BaseModel):
    candidate_id: int
    user_id: int
    name: str
    comment: str

class CommentResponse(BaseModel):
    candidate_id: int
    user_id: int
    name: str
    comment: str

class CandidateWithCommentsResponse(BaseModel):
    candidate_id: int
    name: str
    email: str
    wallet_address: str
    comments: List[CommentResponse]

class SentimentRequest(BaseModel):
    comments: Dict[str, List[str]]

class SentimentResponse(BaseModel):
    predictions: Dict[str, float]

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Instantiate FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Endpoint 1: User Registration
@app.post("/api/users/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Create new user
    new_user = User(
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role,
        wallet_address=user.wallet_address,
        is_approved=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully.", "user_id": new_user.user_id, "name": new_user.name, "role":new_user.role}

# Endpoint 2: Login
@app.post("/api/users/login")
def register_user(user: UserLogin, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="Email not registered")
    # Verify password
    if existing_user.password != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    return {"message": "Login successful", "user_id": existing_user.user_id, "name": existing_user.name, "role": existing_user.role}


# Endpoint 2: Approve User
@app.put("/api/users/approve/{id}")
def approve_user(id: int, user_secret_token: str, db: Session = Depends(get_db)):
    if user_secret_token != secret_token:
        raise HTTPException(status_code=401, detail="Invalid secret token")
    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    db.commit()
    return {"message": "User approved successfully."}

# Endpoint 3: Add Candidate Campaign
@app.post("/api/candidates/campaign")
def add_campaign(candidate_data: CandidateCampaign, user_id: int, db: Session = Depends(get_db)):
    # Check if user exists and is a candidate
    user = db.query(User).filter(User.user_id == user_id, User.role == "candidate").first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found or not a candidate")
    # Create new candidate campaign
    new_campaign = Candidate(
        user_id=user_id,
        age=candidate_data.age,
        gender=candidate_data.gender,
        edu_background=candidate_data.edu_background,
        criminal_cases=candidate_data.criminal_cases,
        goals=candidate_data.goals,
        motive=candidate_data.motive,
        plan_of_action=candidate_data.plan_of_action,
        slogan=candidate_data.slogan
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    return {"message": "Campaign added successfully."}

# Endpoint 5: Add Comment on Campaign
@app.post("/api/comments")
def add_comment(comment_data: CommentRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == comment_data.user_id, User.role == "candidate").first()
    if user:
        raise HTTPException(status_code=400, detail="User not found as a candidate")
    
    # Database connection setup
    pred,prob = sentiment.predict_sentiment(comment_data.comment)
    prob = float(prob)
    # Store comment
    new_comment = Comment(
        candidate_id=comment_data.candidate_id,
        user_id=comment_data.user_id,
        name=comment_data.name,
        comment=comment_data.comment,
        sentiment=pred,
        sentiment_probability=prob
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return {"message": "Comment added successfully."}

@app.get("/api/comments", response_model=List[CandidateWithCommentsResponse])
def get_all_comments(db: Session = Depends(get_db)):
    # Fetch all candidates
    candidates = db.query(User).filter(User.role == "candidate", User.is_approved == True).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found")
    response = []
    for candidate in candidates:
        candidate_comments = db.query(Comment).filter(Comment.candidate_id == candidate.user_id).all()
        comments = [
            CommentResponse(
                candidate_id=comment.candidate_id,
                user_id=comment.user_id,
                name=comment.name,
                comment=comment.comment
            ) for comment in candidate_comments
        ]
        response.append(
            CandidateWithCommentsResponse(
                candidate_id=candidate.user_id,
                name=candidate.name,
                email=candidate.email,
                wallet_address=candidate.wallet_address,
                comments=comments
            )
        )

    return response

# Endpoint 4: Get All Campaigns
@app.get("/api/candidates/campaigns", response_model=List[CampaignResponse])
def get_campaigns(db: Session = Depends(get_db)):
    # Fetch all approved candidates and their campaigns
    campaigns = db.query(Candidate, User).filter(User.user_id == Candidate.user_id, User.is_approved == True).all()
    response = []
    for candidate, user in campaigns:
        campaign_data = CandidateCampaign(
            age=candidate.age,
            gender=candidate.gender,
            edu_background=candidate.edu_background,
            criminal_cases=candidate.criminal_cases,
            goals=candidate.goals,
            motive=candidate.motive,
            plan_of_action=candidate.plan_of_action,
            slogan=candidate.slogan
        )
        response.append(CampaignResponse(
            candidate_id=candidate.candidate_id,
            name=user.name,
            campaign=campaign_data
        ))
    return response

# Endpoint 7: Get All Candidates
@app.get("/api/users/candidates", response_model=List[UserResponse])
def get_all_candidates(db: Session = Depends(get_db)):
    candidates = db.query(User).filter(User.role == "candidate", User.is_approved == False).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found")    
    response = []
    for candidate in candidates:
        response.append(UserResponse(
            user_id= candidate.user_id,
            name= candidate.name,
            email= candidate.email,
            wallet_address= candidate.wallet_address
        ))
    return response


# Endpoint 8: Get All Voters
@app.get("/api/users/voters", response_model=List[UserResponse])
def get_all_voters(db: Session = Depends(get_db)):
    voters = db.query(User).filter(User.role == "voter", User.is_approved == False).all()
    if not voters:
        raise HTTPException(status_code=404, detail="No voters found")
    response = []
    for voter in voters:
            response.append(UserResponse(
                user_id= voter.user_id,
                name= voter.name,
                email= voter.email,
                wallet_address= voter.wallet_address
            ))
    return response

@app.get("/api/users/approved-voters", response_model=List[UserResponse])
def get_approved_voters(db: Session = Depends(get_db)):
    approved_voters = db.query(User).filter(User.role == "voter", User.is_approved == True).all()
    response = []
    for voter in approved_voters:
            response.append(UserResponse(
                name= voter.name,
                user_id= voter.user_id,
                email= voter.email,
                wallet_address= voter.wallet_address 
            ))
    return response

@app.get("/api/users/approved-candidates", response_model=List[UserResponse])
def get_approved_candidates(db: Session = Depends(get_db)):
    approved_candidates = db.query(User).filter(User.role == "candidate", User.is_approved == True).all()
    response = []
    for candidate in approved_candidates:
            response.append(UserResponse(
                user_id= candidate.user_id,
                name= candidate.name,
                email= candidate.email,
                wallet_address= candidate.wallet_address
            ))
    return response

# Endpoint 6: Sentiment Analysis
@app.post("/api/sentiment")
def sentiment_analysis(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    comments = db.query(Comment).all()

    candidate_sentiments = {}

    for candidate in candidates:
        candidate_comments = [comment for comment in comments if comment.candidate_id == candidate.candidate_id]

        if not candidate_comments:
            candidate_sentiments[candidate.candidate_id] = {"sentiment": "neutral", "probability": 0.5}
        else:
            sentiment_scores = {}
            total_probability = sum(comment.sentiment_probability for comment in candidate_comments)

            for comment in candidate_comments:
                sentiment = comment.sentiment
                normalized_prob = comment.sentiment_probability / total_probability
                if sentiment not in sentiment_scores:
                    sentiment_scores[sentiment] = 0
                sentiment_scores[sentiment] += normalized_prob

            majority_sentiment = max(sentiment_scores, key=sentiment_scores.get)
            candidate_sentiments[candidate.candidate_id] = {"sentiment": majority_sentiment, "probability": round(sentiment_scores[majority_sentiment],3)}

    return {"predictions": candidate_sentiments}