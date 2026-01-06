
export interface LakeData {
  name: string;
  temperature: number;
  ph: number;
  turbidity: number;
  dissolvedOxygen: number;
  lastUpdated: string;
  location: string;
}

export enum CallStatus {
  IDLE = 'IDLE',
  CONNECTING = 'CONNECTING',
  ACTIVE = 'ACTIVE',
  ENDED = 'ENDED',
  ERROR = 'ERROR'
}

export interface TranscriptionEntry {
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}
