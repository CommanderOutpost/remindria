from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import timedelta


def refresh_google_access_token(refresh_token, client_id, client_secret):
    """
    Refreshes a Google access token using the provided refresh token.

    Args:
        refresh_token (str): The refresh token for Google APIs.
        client_id (str): The Google OAuth 2.0 client ID.
        client_secret (str): The Google OAuth 2.0 client secret.

    Returns:
        dict: A dictionary containing the new access token and its expiry time.
              Example:
              {
                  "access_token": "string",
                  "expiry": "datetime.datetime"
              }
    Raises:
        Exception: If the refresh process fails.
    """
    try:
        # if not refresh_token or not client_id or not client_secret:
        #     raise
        # Create a credentials object with the refresh token
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        # Refresh the access token
        creds.refresh(Request())

        # Add one hour to the expiry time to ensure the token is valid
        creds.expiry += timedelta(hours=1)

        # Return the new access token and expiry
        return {
            "access_token": creds.token,
            "expiry": creds.expiry,
        }
    except Exception as e:
        raise Exception(f"Failed to refresh token: {str(e)}")


def exchange_auth_code_with_google(auth_code, client_id, client_secret, redirect_uri):
    """
    Exchanges an authorization code for access and refresh tokens using Google's library.

    :param auth_code: The authorization code received from the frontend.
    :param client_id: Your Google OAuth 2.0 client ID.
    :param client_secret: Your Google OAuth 2.0 client secret.
    :param redirect_uri: The redirect URI used in the OAuth flow (must match the Google Console settings).
    :return: A dictionary containing the access_token, refresh_token, and other data.
    :raises: Exception if the token exchange fails.
    """
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.coursework.me",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
        "https://www.googleapis.com/auth/classroom.announcements.readonly",
    ]

    # Configure the OAuth 2.0 flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=scopes,
    )

    # Specify the authorization code and redirect URI
    flow.redirect_uri = redirect_uri

    try:
        # Exchange the authorization code for tokens
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials

        # Add one hour to the expiry time to ensure the token is valid
        credentials.expiry += timedelta(hours=1)

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry": credentials.expiry,
            "scopes": credentials.scopes,
        }
    except Exception as e:
        raise Exception(f"Error exchanging authorization code: {e}")
