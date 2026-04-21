package com.aegis.agent.domain.usecase

/**
 * domain/usecase — Use Case layer (Interactors)
 *
 * In clean architecture a Use Case encapsulates ONE business operation.
 * It sits between the presentation layer (ViewModels / Workers) and the
 * data layer (Repositories), so neither side knows about the other.
 *
 * Use cases added in subsequent prompts:
 *  - CollectDeviceTelemetryUseCase  (Prompt 1.2)
 *  - CollectAppInventoryUseCase     (Prompt 1.3)
 *  - UploadTelemetryUseCase         (Prompt 2.1)
 *
 * Each use case should:
 *  1. Accept only domain models as parameters
 *  2. Return a Result<T> or emit a Flow<T>
 *  3. Have a single public operator fun invoke(...)
 *
 * Example skeleton:
 * ```
 * class MyUseCase @Inject constructor(
 *     private val repository: MyRepository
 * ) {
 *     suspend operator fun invoke(param: DomainModel): Result<OutputModel> {
 *         return repository.doSomething(param)
 *     }
 * }
 * ```
 */
// This file documents the layer — use cases added in Prompts 1.2 and 1.3
