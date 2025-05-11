import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Box, Card, Typography, Divider, Paper } from '@mui/material';

interface ICD10Mapping {
  symptom: string;
  diagnosis: string;
  icd10: string;
}

interface AppointmentPrefill {
  specialty?: string;
  suggestedDate?: string;
  location?: string;
}

export interface StructuredContent {
  symptoms?: string[];
  mappings?: { symptom: string; diagnosis: string }[];
  icd10?: ICD10Mapping[];
  appointment?: AppointmentPrefill; // NEW: Future-proof pre-fill info
}

interface MessageProps {
  role: string;
  content: string | StructuredContent;
}

const Message: React.FC<MessageProps> = ({ role, content }) => {
  const isBot = role === 'assistant';

  const renderStructuredContent = (data: StructuredContent) => {
    const { symptoms, mappings, icd10, appointment } = data;

    return (
      <>
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🩺 Identified Symptoms:
        </Typography>
        <Typography variant="body1">
          {symptoms?.length ? symptoms.join(', ') : 'N/A'}
        </Typography>

        <Divider sx={{ my: 1 }} />

        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🏥 Mapped Clinical Diagnoses:
        </Typography>
        {mappings && mappings.length > 0 ? (
          mappings.map((m, index) => (
            <Typography variant="body1" key={index}>
              • {m.symptom} → <strong>{m.diagnosis}</strong>
            </Typography>
          ))
        ) : (
          <Typography variant="body1">N/A</Typography>
        )}

        <Divider sx={{ my: 1 }} />

        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🗂️ ICD-10 Codes:
        </Typography>
        {icd10 && icd10.length > 0 ? (
          icd10.map((code, idx) => (
            <Typography variant="body1" key={idx}>
              • {code.symptom} → {code.diagnosis} → <strong>{code.icd10}</strong>
            </Typography>
          ))
        ) : (
          <Typography variant="body1">N/A</Typography>
        )}

        {/* Future Appointment Info */}
        {appointment && (
          <>
            <Divider sx={{ my: 2 }} />
            <Paper elevation={2} sx={{ p: 2, backgroundColor: 'grey.100' }}>
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                📅 Suggested Appointment Details:
              </Typography>
              <Typography variant="body1">
                <strong>Specialty:</strong> {appointment.specialty || 'N/A'}
              </Typography>
              <Typography variant="body1">
                <strong>Suggested Date:</strong> {appointment.suggestedDate || 'N/A'}
              </Typography>
              <Typography variant="body1">
                <strong>Location:</strong> {appointment.location || 'N/A'}
              </Typography>
            </Paper>
          </>
        )}
      </>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isBot ? 'flex-start' : 'flex-end',
        mb: 1,
      }}
    >
      <Card
        sx={{
          maxWidth: '60%',
          p: 2,
          borderRadius: '16px',
          boxShadow: 3,
          backgroundColor: isBot ? 'blue.100' : 'grey.300',
          color: isBot ? 'grey.900' : 'common.black',
        }}
      >
        <Typography variant="subtitle1" component="strong" gutterBottom>
          {isBot ? 'VocaMedBot' : 'You'}:
        </Typography>

        {typeof content === 'string' ? (
          <ReactMarkdown>{content}</ReactMarkdown>
        ) : (
          renderStructuredContent(content)
        )}
      </Card>
    </Box>
  );
};

export default Message;
