interface User {
    id: number;
    name: string;
}

import { formatDate, generateId } from "./utils/helpers";

class DatabaseConnection {
    private connectionString: string;
    private instanceId: string;

    constructor(uri: string) {
        this.connectionString = uri;
        this.instanceId = generateId();
    }

    async connect(): Promise<void> {
        console.log(`Connecting to database at ${this.connectionString} [${formatDate(new Date())}]`);
    }

    async query(sql: string, params: any[]): Promise<any> {
        console.log(`Executing query: ${sql}`);
        return [];
    }

    disconnect(): void {
        console.log("Database disconnected.");
    }
}

export function createDatabase(uri: string): DatabaseConnection {
    return new DatabaseConnection(uri);
}
