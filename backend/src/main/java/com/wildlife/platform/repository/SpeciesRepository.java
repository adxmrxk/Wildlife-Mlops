package com.wildlife.platform.repository;

import com.wildlife.platform.model.Species;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface SpeciesRepository extends JpaRepository<Species, Long> {

    // Find a species by its scientific name
    Optional<Species> findByName(String name);

    // That's it! JpaRepository gives us these methods for FREE:
    // - save(Species) - save or update
    // - findById(Long) - find by ID
    // - findAll() - get all species
    // - deleteById(Long) - delete by ID
    // - count() - count total species
    // And many more!
}
