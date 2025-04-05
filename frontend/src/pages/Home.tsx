import React, { useState } from "react";
import { Container, Typography, Button, Box, Grid, Paper, Fab, Dialog } from "@mui/material";
import { Chat, MedicalServices, Security, RecordVoiceOver } from "@mui/icons-material";
import ChatComponent from "../components/Chat";

const HomePage = () => {
  const [openChat, setOpenChat] = useState(false);

  return (
    <Container maxWidth="lg" sx={{ textAlign: "center", py: 8 }}>
      {/* Hero Section */}
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" gutterBottom>
          From Voice to Booking
        </Typography>
        <Typography variant="h6" color="textSecondary" gutterBottom>
          A real-time edge AI assistant for symptom extraction and clinical appointment pre-fill.
        </Typography>
        <Button
          variant="contained"
          color="primary"
          size="large"
          sx={{ mt: 2 }}
          onClick={() => setOpenChat(true)}
        >
          Try Voice Chat
        </Button>
      </Box>

      {/* Features Section */}
      <Grid container spacing={4} sx={{ mt: 6 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <RecordVoiceOver fontSize="large" color="primary" />
            <Typography variant="h6" gutterBottom>
              Voice-to-Symptom Conversion
            </Typography>
            <Typography color="textSecondary">
              Speak freely and let our AI extract your symptoms using state-of-the-art transcription and NLP.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <MedicalServices fontSize="large" color="secondary" />
            <Typography variant="h6" gutterBottom>
              Automated Appointment Pre-Fill
            </Typography>
            <Typography color="textSecondary">
              Matched symptoms are mapped to medical specializations and filled into a booking interface.
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <Security fontSize="large" color="success" />
            <Typography variant="h6" gutterBottom>
              Edge-Powered Privacy
            </Typography>
            <Typography color="textSecondary">
              Runs locally on Raspberry Pi for low-latency, privacy-preserving deployments in clinics and kiosks.
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Floating Chat Button */}
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
