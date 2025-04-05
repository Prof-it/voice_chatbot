import React, { useState } from "react";
import { Container, Typography, Button, Box, Grid, Paper, Fab, Dialog } from "@mui/material";
import {Chat , MedicalServices, Security } from "@mui/icons-material";
import ChatComponent from "../components/Chat";


const HomePage = () => {
  const [openChat, setOpenChat] = useState(false);

  return (
    <Container maxWidth="lg" sx={{ textAlign: "center", py: 8 }}>
      {/* Hero Section */}
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" gutterBottom>
          Welcome to ENTChatBot
        </Typography>
        <Typography variant="h6" color="textSecondary" gutterBottom>
          AI-powered assistance for all your Ear, Nose, and Throat health queries.
        </Typography>
        <Button variant="contained" color="primary" size="large" sx={{ mt: 2 }}>
          Get Started
        </Button>
      </Box>

      {/* Features Section */}
      <Grid container spacing={4} sx={{ mt: 6 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <Chat fontSize="large" color="primary" />
            <Typography variant="h6" gutterBottom>
              Smart Symptom Checker
            </Typography>
            <Typography color="textSecondary">
              Get instant insights based on your symptoms with our AI-powered chatbot.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <MedicalServices fontSize="large" color="secondary" />
            <Typography variant="h6" gutterBottom>
              Side-Effect Checker
            </Typography>
            <Typography color="textSecondary">
              Check possible medication side effects before taking any drugs.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <Security fontSize="large" color="success" />
            <Typography variant="h6" gutterBottom>
              Secure & Reliable
            </Typography>
            <Typography color="textSecondary">
            We prioritize your privacy and do not store any chat data. However, if this changes in the future, we’ll make sure to inform you.
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Chat Icon Button */}
      <Fab 
        color="primary" 
        aria-label="chat" 
        sx={{ position: "fixed", bottom: 16, right: 16 }} 
        onClick={() => setOpenChat(true)}
      >
        <Chat />
      </Fab>

      {/* Chat Dialog */}
      <Dialog open={openChat} onClose={() => setOpenChat(false)} fullWidth maxWidth="md">
        <ChatComponent />
      </Dialog>
    </Container>
  );
};

export default HomePage;
