require('dotenv').config(); // Load .env
const express = require('express');
const mongoose = require('mongoose');

const app = express();

// Middleware for JSON requests
app.use(express.json());

// Connect to MongoDB via Mongoose
mongoose
  .connect(process.env.MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  })
  .then(() => {
    console.log('Connected to MongoDB');
  })
  .catch((err) => {
    console.error('Error connecting to MongoDB:', err);
  });

// server.js
const authRoutes = require('./routes/authRoutes');
app.use('/api/auth', authRoutes);

// Example route to check if server is running
app.get('/', (req, res) => {
  res.send('Hello from Job Tracker App!');
});

// Use external routes (example: userRoutes)
const userRoutes = require('./routes/userRoutes');
app.use('/api/users', userRoutes);

// Start listening on specified port
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
