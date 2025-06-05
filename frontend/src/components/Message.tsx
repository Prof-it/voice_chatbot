import {
  Box,
  Card,
  Typography,
  useTheme
} from '@mui/material';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import StructuredMessageContent, { StructuredContent } from './StructuredMessageContent';

// Update MessageProps to include the new timing fields
// Make sure this aligns with the MessageData interface in your Chat.tsx
interface MessageProps {
  role: "user" | "assistant"; // Make role more specific if possible
  content: string | StructuredContent;
  responseTimeMs?: number;
  ttfbMs?: number;
  transcriptionTimeMs?: number;
}

const Message: React.FC<MessageProps> = ({
  role,
  content,
  responseTimeMs,
  ttfbMs,
  transcriptionTimeMs,
}) => {
  const isBot = role === 'assistant';
  const theme = useTheme();

  console.log('Rendering Message component:', content, typeof content);
  const maybeStructured = (() => {
    if (typeof content !== "string") return null;
    try {
      const obj = JSON.parse(content);
      // crude shape check – tweak as you like
      if (obj && (obj.symptoms || obj.icd10 || obj.appointment)) {
        return obj as StructuredContent;
      }
    } catch { /* not JSON */ }
    return null;
  })();


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
          display: 'flex', // Added to allow metrics to be below content
          flexDirection: 'column', // Stack content and metrics vertically
        }}
      >
        <Box> {/* Wrapper for main content part */}
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            {isBot ? 'VoiceMediAI Bot' : 'You'}:
          </Typography>

          {maybeStructured ? (
            <StructuredMessageContent data={maybeStructured} />
          ) : typeof content === "string" ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            <StructuredMessageContent data={content} />
          )}
        </Box>

        {/* Conditional rendering for metrics */}
        {(role === 'assistant' && responseTimeMs !== undefined) ||
          (role === 'user' && transcriptionTimeMs !== undefined) ? (
          <Box sx={{ mt: 1.5, pt: 1, borderTop: `1px solid ${theme.palette.divider}` }}>
            {role === 'assistant' && responseTimeMs !== undefined && (
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                {ttfbMs !== undefined && `TTFB: ${ttfbMs}ms | `}
                Response: {responseTimeMs}ms
              </Typography>
            )}
            {role === 'user' && transcriptionTimeMs !== undefined && (
              <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                Transcription: {transcriptionTimeMs}ms
              </Typography>
            )}
          </Box>
        ) : null}
      </Card>
    </Box>
  );
};

export default Message;