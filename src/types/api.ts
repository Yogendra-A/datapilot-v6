export type Status = 'passed' | 'failed' | 'not_evaluated';
export type AgentStepState = 'complete' | 'active' | 'pending';
export interface AgentStep { label: string; detail: string; state: AgentStepState; }
export interface QueryRequest { question: string; database_id: string; }
export interface QueryResponse { question: string; generated_sql: string; validation: Status; execution: Status; columns: string[]; rows: Array<Record<string, string | number>>; final_answer: string; verification: { semantic: Status; result: Status; grounding: Status }; execution_time: number; agent_steps: AgentStep[]; is_demo: boolean; }
export interface TableColumn { name: string; type: string; key?: 'PK' | 'FK'; }
export interface DatabaseTable { name: string; columns: TableColumn[]; }
export interface DatabaseSchemaResponse { database_type: string; database_name: string; tables: DatabaseTable[]; relationships: string[]; connected: boolean; }
export interface HistoryItem { id: string; question: string; timestamp: string; status: Status; rows: number; duration: number; }
export interface EvaluationResponse { total: number | null; passed: number | null; failed: number | null; metrics: Record<string, number | null>; cases: Array<{ test_case: string; expected: string; actual: string; sql_status: Status; verification: Status }>; }
