import React from 'react';
import { Typography, Divider, Paper } from '@mui/material';

export interface ICD10Mapping {
  symptom: string;
  diagnosis: string;
  icd10: string;
}

export interface AppointmentPrefill {
  specialty?: string;
  suggestedDate?: string;
  location?: string;
}

export interface FHIRCondition {
  resourceType: 'Condition';
  clinicalStatus: { text: string };
  verificationStatus: { text: string };
  code: { text: string };
}

export interface FHIRAppointment {
  resourceType: 'Appointment';
  status: string;
  description?: string;
  start?: string;
  end?: string;
}

export interface StructuredContent {
  symptoms?: string[];
  mappings?: { symptom: string; diagnosis: string }[];
  icd10?: ICD10Mapping[];
  appointment?: AppointmentPrefill;
  symptoms_fhir?: FHIRCondition[];
  appointment_fhir?: FHIRAppointment;
}

const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return isNaN(date.getTime())
      ? dateString // fallback to raw string if parsing fails
      : date.toLocaleString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
  };

const StructuredMessageContent: React.FC<{ data: StructuredContent }> = ({ data }) => {
  const { symptoms, mappings, icd10, appointment, symptoms_fhir, appointment_fhir } = data;

  return (
    <>
      {/* Symptoms */}
      <Section title="🩺 Identified Symptoms" content={symptoms?.join(', ') || 'N/A'} />

      {/* Mappings */}
      <Section title="🏥 Mapped Clinical Diagnoses">
        {mappings?.length ? (
          mappings.map((m, i) => (
            <Typography variant="body1" key={i}>
              • {m.symptom} → <strong>{m.diagnosis}</strong>
            </Typography>
          ))
        ) : (
          <Typography variant="body1">N/A</Typography>
        )}
      </Section>

      {/* ICD-10 Codes */}
      <Section title="🗂️ ICD-10 Codes">
        {icd10?.length ? (
          icd10.map((item, i) => (
            <Typography variant="body1" key={i}>
              • {item.symptom} → {item.diagnosis} → <strong>{item.icd10}</strong>
            </Typography>
          ))
        ) : (
          <Typography variant="body1">N/A</Typography>
        )}
      </Section>

      {/* FHIR Symptoms */}
      {(symptoms_fhir ?? []).length > 0 && (
        <Section title="🧬 FHIR: Structured Symptom Data">
          {symptoms_fhir?.map((item, i) => (
            <Typography variant="body2" key={i}>
              • <strong>{item.code.text}</strong> — Status: {item.clinicalStatus.text}, Verified: {item.verificationStatus.text}
            </Typography>
          ))}
        </Section>
      )}

      {/* FHIR Appointment */}
      {appointment_fhir && (
        <Section title="🗓️ FHIR: Appointment Object">
          <Typography variant="body2">
            <strong>Status:</strong> {appointment_fhir.status}
          </Typography>
          <Typography variant="body2">
            <strong>Description:</strong> {appointment_fhir.description || 'N/A'}
          </Typography>
          <Typography variant="body2">
            <strong>Start:</strong> {formatDate(appointment_fhir.start) || 'N/A'}
          </Typography>
          <Typography variant="body2">
            <strong>End:</strong> {formatDate(appointment_fhir.end) || 'N/A'}
          </Typography>
        </Section>
      )}
    </>
  );
};

const Section: React.FC<{ title: string; content?: React.ReactNode; children?: React.ReactNode }> = ({ title, content, children }) => (
  <>
    <Divider sx={{ my: 2 }} />
    <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
      {title}
    </Typography>
    {content ? <Typography variant="body1">{content}</Typography> : children}
  </>
);

export default StructuredMessageContent;
