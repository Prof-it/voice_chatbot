import React from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Box,
  Card,
  Typography,
  useTheme,
} from '@mui/material';
import  StructuredMessageContent, { StructuredContent } from './StructuredMessageContent';

interface MessageProps {
  role: string;
  content: string | StructuredContent;
}

const Message: React.FC<MessageProps> = ({ role, content }) => {
  const isBot = role === 'assistant';
  const theme = useTheme();

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
          maxWidth: { xs: '100%', sm: '75%', md: '60%' },
          p: 2,
          borderRadius: 3,
          boxShadow: 3,
          backgroundColor: isBot ? theme.palette.grey[100] : theme.palette.grey[300],
          color: theme.palette.text.primary,
        }}
      >
        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
          {isBot ? 'VoiceMediAI Bot' : 'You'}:
        </Typography>

        {typeof content === 'string' ? (
          <ReactMarkdown>{content}</ReactMarkdown>
        ) : (
          <StructuredMessageContent data={content} />
        )}
      </Card>
    </Box>
  );
};

export default Message;
