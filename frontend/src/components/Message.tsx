import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Box, Card, Typography, Divider } from '@mui/material';

interface StructuredContent {
  symptoms?: string[];
  disease?: string;  
  drugs?: Record<string, any>;  // drugs can either be drug name => fields, or { error: string }
}

interface MessageProps {
  role: string;
  content: string | StructuredContent;
}

const Message: React.FC<MessageProps> = ({ role, content }) => {
  const isBot = role === 'assistant';  

  const renderStructuredContent = (data: StructuredContent) => {
    
    const { symptoms, disease, drugs } = data;

    return (
      <>
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🩺 Identified Symptoms:
        </Typography>
        <Typography variant="body1">{symptoms?.join(', ') || "N/A"}</Typography>

        <Divider sx={{ my: 1 }} />

        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🏥 Predicted Condition:
        </Typography>
        <Typography variant="body1">{disease || "N/A"}</Typography>

        <Divider sx={{ my: 1 }} />

        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          💊 Recommended Medications:
        </Typography>

        {drugs?.error ? (
          <Typography variant="body2" color="error">
            🚫 {drugs.error}
          </Typography>
        ) : drugs && Object.keys(drugs).length > 0 ? (
          Object.entries(drugs).map(([drugName, fields]) => (
            <Box key={drugName} sx={{ mb: 2, pl: 1 }}>
              <Typography variant="body1" fontWeight="bold" color="primary">
                • {drugName}
              </Typography>
              {Object.entries(fields).map(([fieldName, fieldValue]) => (
                <Box key={fieldName} sx={{ pl: 2, mb: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {fieldName.replace(/_/g, ' ')}:
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {String(fieldValue)}
                  </Typography>
                </Box>
              ))}
            </Box>
          ))
        ) : (
          <Typography variant="body2">N/A</Typography>
        )}

        <Divider sx={{ my: 1 }} />


        <Typography variant="caption" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
          🔔 Note: Always Consult a healthcare professional before taking any medication.
        </Typography>
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
          {isBot ? 'ENTBot' : 'You'}:
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
