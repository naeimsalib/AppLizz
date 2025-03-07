const User = require('../models/User');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// REGISTER
exports.registerUser = async (req, res) => {
  try {
    const { email, password } = req.body;

    // Check if all required data is provided
    if (!email || !password) {
      return res.status(400).json({ msg: 'Missing email or password' });
    }

    // Check if user already exists
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ msg: 'User already exists' });
    }

    // Hash password
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Create new user
    const newUser = new User({
      email,
      password: hashedPassword,
    });

    // Save user to DB
    await newUser.save();
    return res.status(201).json({ msg: 'User registered successfully' });
  } catch (err) {
    console.error('Error registering user:', err);
    return res.status(500).json({ msg: 'Server Error' });
  }
};

// LOGIN
exports.loginUser = async (req, res) => {
  try {
    const { email, password } = req.body;

    // Check if all required data is provided
    if (!email || !password) {
      return res.status(400).json({ msg: 'Missing email or password' });
    }

    // Find the user
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(400).json({ msg: 'Invalid credentials' });
    }

    // Compare input password with stored hashed password
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ msg: 'Invalid credentials' });
    }

    // Create a JWT payload
    const payload = {
      userId: user._id,
      email: user.email,
    };

    // Sign the token
    const token = jwt.sign(payload, process.env.JWT_SECRET, {
      expiresIn: '1d', // Token valid for 1 day
    });

    // Return the token
    return res.status(200).json({ msg: 'Logged in successfully', token });
  } catch (err) {
    console.error('Error logging in user:', err);
    return res.status(500).json({ msg: 'Server Error' });
  }
};
