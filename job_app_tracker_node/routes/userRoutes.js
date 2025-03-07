// routes/userRoutes.js
const express = require('express');
const { createUser, getAllUsers } = require('../controllers/userController');

const router = express.Router();

// POST /api/users - Create a new user
router.post('/', createUser);

// GET /api/users - Get all users
router.get('/', getAllUsers);

module.exports = router;
