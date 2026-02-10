"""Tests for the Mergington High School API endpoints"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        
        # Verify structure of one activity
        assert "Soccer Team" in data
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)
    
    def test_get_activities_includes_all_fields(self, client):
        """Test that activities include all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity, f"{activity_name} missing description"
            assert "schedule" in activity, f"{activity_name} missing schedule"
            assert "max_participants" in activity, f"{activity_name} missing max_participants"
            assert "participants" in activity, f"{activity_name} missing participants"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Soccer Team"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_registration(self, client):
        """Test that duplicate registration is prevented"""
        email = "duplicate@mergington.edu"
        activity = "Soccer Team"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Math%20Olympiad/signup?email=mathstudent@mergington.edu"
        )
        assert response.status_code == 200
    
    def test_signup_preserves_existing_participants(self, client):
        """Test that signup doesn't remove existing participants"""
        # Get initial participant count
        activities_before = client.get("/activities").json()
        initial_count = len(activities_before["Swimming Club"]["participants"])
        initial_participants = activities_before["Swimming Club"]["participants"].copy()
        
        # Add new participant
        client.post("/activities/Swimming Club/signup?email=newswimmer@mergington.edu")
        
        # Verify all participants are still there
        activities_after = client.get("/activities").json()
        final_participants = activities_after["Swimming Club"]["participants"]
        
        assert len(final_participants) == initial_count + 1
        for participant in initial_participants:
            assert participant in final_participants


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        activity = "Soccer Team"
        email = "alex@mergington.edu"
        
        # Verify participant exists
        activities_before = client.get("/activities").json()
        assert email in activities_before[activity]["participants"]
        
        # Remove participant
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was removed
        activities_after = client.get("/activities").json()
        assert email not in activities_after[activity]["participants"]
    
    def test_remove_participant_activity_not_found(self, client):
        """Test removal from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "Activity not found" in data["detail"]
    
    def test_remove_participant_not_in_activity(self, client):
        """Test removal of participant not in activity"""
        response = client.delete(
            "/activities/Soccer Team/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_remove_participant_with_encoded_email(self, client):
        """Test removal with URL-encoded email"""
        activity = "Drama Club"
        email = "isabella@mergington.edu"
        
        # URL encode the email (@ becomes %40)
        encoded_email = email.replace("@", "%40")
        
        response = client.delete(f"/activities/{activity}/participants/{encoded_email}")
        assert response.status_code == 200
        
        # Verify removal
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]
    
    def test_remove_participant_preserves_others(self, client):
        """Test that removing one participant doesn't affect others"""
        activity = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        email_to_keep = "daniel@mergington.edu"
        
        # Remove one participant
        response = client.delete(f"/activities/{activity}/participants/{email_to_remove}")
        assert response.status_code == 200
        
        # Verify the other participant is still there
        activities = client.get("/activities").json()
        participants = activities[activity]["participants"]
        assert email_to_remove not in participants
        assert email_to_keep in participants


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow of signing up and removing"""
        activity = "Art Studio"
        email = "artlover@mergington.edu"
        
        # Get initial state
        initial_activities = client.get("/activities").json()
        initial_count = len(initial_activities[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        assert email in after_signup[activity]["participants"]
        
        # Remove
        remove_response = client.delete(f"/activities/{activity}/participants/{email}")
        assert remove_response.status_code == 200
        
        # Verify removal
        after_removal = client.get("/activities").json()
        assert len(after_removal[activity]["participants"]) == initial_count
        assert email not in after_removal[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multitasker@mergington.edu"
        activities = ["Soccer Team", "Math Olympiad", "Programming Class"]
        
        for activity in activities:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities:
            assert email in all_activities[activity]["participants"]
