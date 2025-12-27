import torch
import torch.nn as nn
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

class SimpleVulnerabilityNN(nn.Module):
    def __init__(self, input_dim=100):
        super(SimpleVulnerabilityNN, self).__init__()
        
        self.vectorizer = CountVectorizer(max_features=input_dim, stop_words='english')
        
        dummy_data = [
            "SQL syntax error in query",
            "Warning: mysql_fetch_array()",
            "Unclosed quotation mark after the character string",
            "Index of /admin",
            "reflected XSS payload <script>alert(1)</script>",
            "Normal page content",
            "Welcome to our website",
            "Contact us for more information",
            "Copyright 2024",
            "Home page"
        ]
        dummy_labels = torch.tensor([[1.0], [1.0], [1.0], [1.0], [1.0], [0.0], [0.0], [0.0], [0.0], [0.0]])
        
        self.vectorizer.fit(dummy_data)
        X = self.vectorizer.transform(dummy_data).toarray()
        actual_dim = X.shape[1]
        
        self.fc1 = nn.Linear(actual_dim, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 1)
        self.sigmoid = nn.Sigmoid()
        
        X_tensor = torch.FloatTensor(X)
        
        optimizer = torch.optim.Adam(self.parameters(), lr=0.01)
        criterion = nn.BCELoss()
        
        for _ in range(50):
            optimizer.zero_grad()
            outputs = self(X_tensor)
            loss = criterion(outputs, dummy_labels)
            loss.backward()
            optimizer.step()

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        output = self.sigmoid(x)
        return output

    def predict(self, text):
        try:
            vectorized = self.vectorizer.transform([text]).toarray()
            tensor = torch.FloatTensor(vectorized)
            with torch.no_grad():
                prediction = self(tensor)
            return prediction.item()
        except Exception:
            return 0.0
