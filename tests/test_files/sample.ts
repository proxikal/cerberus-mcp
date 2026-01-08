// This is a sample TypeScript file for testing the parser.

import path from "path";

export class MyTsClass {
    constructor(public name: string) {}

    greet(): string {
        return `Hello, ${this.name}`;
    }
}

export function topLevelTsFunction(a: number, b: number): number {
    path.join("a", "b");
    return a + b;
}

export interface UserProfile {
    name: string;
    age: number;
}

export enum Status {
    Active = "active",
    Inactive = "inactive"
}
