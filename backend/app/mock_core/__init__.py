"""Local simulator of the CORE module (auth, JWKS, wallet, notifications).

The current delivery runs WITHOUT the other UADEnet modules, so the portal needs somewhere to log in,
see its balance and receive notifications. Enabled with MOCK_CORE_ENABLED=true; every path and payload
copies the real CORE contract, so pointing the frontend at the real CORE later is a base-URL change.
"""
