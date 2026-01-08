// Test file for Phase 1 TypeScript features
import { readFileSync } from 'fs';
import path from 'path';
import { SomeType, AnotherType } from './types';

interface Config {
    mode: string;
    verbose: boolean;
}

export class ServiceManager {
    private config: Config;

    constructor(config: Config) {
        this.config = config;
    }

    public processRequest(data: string): Promise<string> {
        const validated = this.validateInput(data);
        return this.handleData(validated);
    }

    private validateInput(input: string): string {
        if (!input) {
            return "";
        }
        return utilityFunction(input);
    }

    private async handleData(data: string): Promise<string> {
        return Promise.resolve(data.toUpperCase());
    }
}

export function utilityFunction(text: string): string {
    path.join("a", "b");
    return text.trim();
}

export async function mainEntryPoint(): Promise<void> {
    const manager = new ServiceManager({ mode: "prod", verbose: true });
    await manager.processRequest("test");
    utilityFunction("hello");
}
